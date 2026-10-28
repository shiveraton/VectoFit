from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.analytics.services.segmentation import (
    _deduplicate_repetitions,
    segment_reps,
    split_contiguous_pose_runs,
)
from apps.analytics.services.session_report import build_session_report
from apps.assessments.models import AssessmentSession, RepAssessment
from apps.exercises.models import ExerciseVariant

User = get_user_model()


def _hip_frame(y):
    return {
        "left_hip": {"y": y},
        "right_hip": {"y": y},
    }


def _complete_rep(amplitude=55.0):
    top = 95.0
    bottom = top + amplitude
    values = [110, 100, top]
    values.extend(top + step * (bottom - top) / 10 for step in range(1, 11))
    values.extend(bottom - step * (bottom - top) / 10 for step in range(1, 11))
    values.extend([top + 5, top + 10])
    return [_hip_frame(value) for value in values]


def _paced_complete_rep(amplitude=55.0, phase_frames=30):
    top = 95.0
    bottom = top + amplitude
    values = [top + 15, top + 5, top]
    values.extend(
        top + step * (bottom - top) / phase_frames
        for step in range(1, phase_frames + 1)
    )
    values.extend(
        bottom - step * (bottom - top) / phase_frames
        for step in range(1, phase_frames + 1)
    )
    values.extend([top + 5, top + 10])
    return [_hip_frame(value) for value in values]


class RepetitionSegmentationRegressionTests(APITestCase):
    def test_rejects_timed_candidate_without_meaningful_movement(self):
        self.assertEqual(segment_reps(_complete_rep(amplitude=20.0)), [])

    def test_accepts_valid_rep_and_returns_local_boundaries(self):
        repetitions = segment_reps(_complete_rep())

        self.assertEqual(len(repetitions), 1)
        repetition = repetitions[0]
        self.assertLess(repetition["start"], repetition["bottom"])
        self.assertLess(repetition["bottom"], repetition["end"])

    def test_accepts_realistic_long_phase_rep(self):
        repetitions = segment_reps(_paced_complete_rep())

        self.assertEqual(len(repetitions), 1)
        self.assertGreaterEqual(
            repetitions[0]["bottom"] - repetitions[0]["start"],
            10,
        )
        self.assertGreaterEqual(
            repetitions[0]["end"] - repetitions[0]["bottom"],
            10,
        )

    def test_rejects_sequence_without_squat_movement(self):
        self.assertEqual(segment_reps([_hip_frame(120.0)] * 80), [])

    def test_rejects_complete_timing_without_required_amplitude(self):
        self.assertEqual(
            segment_reps(_paced_complete_rep(amplitude=20.0)),
            [],
        )

    def test_missing_pose_splits_runs_and_preserves_original_frame_indices(self):
        landmark_data = [
            {"frame_index": index, "landmarks": landmarks}
            for index, landmarks in enumerate(_complete_rep())
        ]
        landmark_data[10]["landmarks"] = None

        runs = split_contiguous_pose_runs(landmark_data, expected_frame_step=1)

        self.assertEqual([len(run) for run in runs], [10, len(landmark_data) - 11])
        self.assertEqual(runs[1][0]["frame_index"], 11)
        self.assertEqual(runs[0][-1]["frame_index"], 9)
        self.assertEqual(segment_reps([entry["landmarks"] for entry in runs[0]]), [])
        self.assertEqual(segment_reps([entry["landmarks"] for entry in runs[1]]), [])

    def test_substantial_original_frame_gap_is_not_treated_as_contiguous(self):
        series = _paced_complete_rep()
        landmark_data = [
            {"frame_index": index if index < 20 else index + 15, "landmarks": landmarks}
            for index, landmarks in enumerate(series)
        ]

        runs = split_contiguous_pose_runs(landmark_data, expected_frame_step=1)

        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0][-1]["frame_index"], 19)
        self.assertEqual(runs[1][0]["frame_index"], 35)

    def test_overlapping_candidates_keep_the_deeper_candidate(self):
        signal = [100.0, 150.0, 100.0, 140.0, 100.0]
        candidates = [
            {"start": 0, "bottom": 1, "end": 3},
            {"start": 1, "bottom": 3, "end": 4},
        ]

        self.assertEqual(
            _deduplicate_repetitions(candidates, signal),
            [candidates[0]],
        )


def _create_session_with_reps(user, variant, hybrid_score, created_at=None):
    session = AssessmentSession.objects.create(user=user, exercise_variant=variant)
    if created_at is not None:
        AssessmentSession.objects.filter(pk=session.pk).update(created_at=created_at)
        session.refresh_from_db()
    for i, score in enumerate(hybrid_score, start=1):
        RepAssessment.objects.create(
            session=session, rep_number=i, hybrid_score=score, landmark_series=[]
        )
    return session


class WeeklyTrendViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jhed", password="pass12345")
        self.other_user = User.objects.create_user(
            username="other", password="pass 12345"
        )
        self.variant = ExerciseVariant.objects.create(
            name="Bodyweight Squat", variant_type=ExerciseVariant.VariantType.BODYWEIGHT
        )
        self.client.force_authenticate(self.user)

    def test_this_week_aggregates_only_this_weeks_reps(self):
        week_start = timezone.localdate() - timedelta(
            days=timezone.localdate().weekday()
        )

        _create_session_with_reps(
            self.user, self.variant, [80.0, 90.0], created_at=timezone.now()
        )

        _create_session_with_reps(
            self.user,
            self.variant,
            [10.0],
            created_at=timezone.now() - timezone.timedelta(days=14),
        )

        response = self.client.get(reverse("weekly-trend-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["session_count"], 1)
        self.assertEqual(response.data["rep_count"], 2)
        self.assertEqual(response.data["avg_hybrid_score"], 85.0)
        self.assertEqual(response.data["week_start"], week_start.isoformat())

    def test_other_users_reps_excluded(self):
        _create_session_with_reps(self.other_user, self.variant, [50.0])

        response = self.client.get(reverse("weekly-trend-list"))

        self.assertEqual(response.data["session_count"], 0)
        self.assertEqual(response.data["rep_count"], 0)
        self.assertIsNone(response.data["avg_hybrid_score"])

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("weekly-trend-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TrendSeriesViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jhed", password="pass12345")
        self.variant = ExerciseVariant.objects.create(
            name="Goblet Squat", variant_type=ExerciseVariant.VariantType.GOBLET
        )
        self.client.force_authenticate(self.user)

    def test_buckets_by_week_by_default(self):
        _create_session_with_reps(
            self.user, self.variant, [70.0], created_at=timezone.now()
        )

        response = self.client.get(reverse("trend-series-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["rep_count"], 1)

    def test_month_period_param(self):
        _create_session_with_reps(
            self.user, self.variant, [70.0], created_at=timezone.now()
        )

        response = self.client.get(reverse("trend-series-list"), {"period": "month"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class VariantTrendViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jhed", password="pass12345")
        self.bw_variant = ExerciseVariant.objects.create(
            name="Bodyweight Squat", variant_type=ExerciseVariant.VariantType.BODYWEIGHT
        )
        self.goblet_variant = ExerciseVariant.objects.create(
            name="Goblet Squat", variant_type=ExerciseVariant.VariantType.GOBLET
        )
        self.client.force_authenticate(self.user)

    def test_filters_to_requested_variant_only(self):
        _create_session_with_reps(
            self.user, self.bw_variant, [80.0], created_at=timezone.now()
        )

        response = self.client.get(
            reverse("variant-trend-detail", args=[self.bw_variant.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["exercise_variant_name"], "Bodyweight Squat")

        self.assertEqual(len(response.data["points"]), 1)
        self.assertEqual(response.data["points"][0]["rep_count"], 1)


class SessionReportBuilderTests(APITestCase):
    def setUp(self):
        self.thresholds = {
            "knee_depth": 90.0,
            "trunk_lean": 45.0,
            "asymmetry": 10.0,
        }

    def make_rep(self, number, metrics=None, classifications=None):
        return {
            "rep_number": number,
            "analysis_result": {
                "metrics": metrics or {},
                "classifications": classifications or {},
            },
        }

    def classification(
        self,
        value,
        evaluation=None,
    ):
        return {
            "classification": value,
            "evaluation": evaluation or {},
        }

    def test_clean_session_has_no_findings(self):
        acceptable = {
            "knee_angle": self.classification("acceptable"),
            "trunk_angle": self.classification("acceptable"),
            "asymmetry": self.classification("acceptable"),
        }

        reps = [
            self.make_rep(
                1,
                {
                    "knee_angle": 85.0,
                    "trunk_angle": [15.0, 20.0],
                    "asymmetry": 5.0,
                },
                acceptable,
            ),
            self.make_rep(
                2,
                {
                    "knee_angle": 82.0,
                    "trunk_angle": [18.0, 22.0],
                    "asymmetry": 6.0,
                },
                acceptable,
            ),
        ]

        report = build_session_report(reps, self.thresholds)

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["verdict"]["status"], "clean")
        self.assertEqual(report["verdict"]["clean_reps"], 2)
        self.assertEqual(report["verdict"]["total_reps"], 2)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["reps"][0]["flags"], [])
        self.assertIsNone(report["scores"])

    def test_mixed_session_detects_constant_and_worsening_patterns(self):
        reps = []

        for number in range(1, 6):
            asymmetry_excess = number <= 4
            trunk_excess = number >= 4

            metrics = {
                "knee_angle": 82.0,
                "trunk_angle": [
                    15.0,
                    61.0 if trunk_excess else 20.0,
                ],
                "asymmetry": 15.0 if asymmetry_excess else 5.0,
            }

            classifications = {
                "knee_angle": self.classification("acceptable"),
                "trunk_angle": self.classification(
                    "excessive_trunk_lean" if trunk_excess else "acceptable",
                    {
                        "maximum_measured_lean_deg": (61.0 if trunk_excess else 20.0),
                        "maximum_allowed_lean_deg": 45.0,
                        "difference": 16.0 if trunk_excess else 0.0,
                    },
                ),
                "asymmetry": self.classification(
                    "excessive" if asymmetry_excess else "acceptable",
                    {
                        "measured_asymmetry": (15.0 if asymmetry_excess else 5.0),
                        "maximum_asymmetry": 10.0,
                        "difference": 5.0 if asymmetry_excess else 0.0,
                    },
                ),
            }

            reps.append(self.make_rep(number, metrics, classifications))

        report = build_session_report(reps, self.thresholds)

        by_code = {finding["code"]: finding for finding in report["findings"]}

        self.assertEqual(
            by_code["EXCESSIVE_ASYMMETRY"]["affected_reps"],
            [1, 2, 3, 4],
        )
        self.assertEqual(
            by_code["EXCESSIVE_ASYMMETRY"]["pattern"],
            "constant",
        )
        self.assertEqual(
            by_code["EXCESSIVE_TRUNK_LEAN"]["affected_reps"],
            [4, 5],
        )
        self.assertEqual(
            by_code["EXCESSIVE_TRUNK_LEAN"]["pattern"],
            "worsening",
        )
        self.assertEqual(report["verdict"]["status"], "needs_work")

    def test_missing_metrics_do_not_crash_aggregation(self):
        reps = [
            self.make_rep(1, {}, {}),
            self.make_rep(
                2,
                {
                    "knee_angle": 84.0,
                    "trunk_angle": [15.0, 24.0],
                    "asymmetry": 5.0,
                },
                {
                    "knee_angle": self.classification("acceptable"),
                    "trunk_angle": self.classification("acceptable"),
                    "asymmetry": self.classification("acceptable"),
                },
            ),
        ]

        report = build_session_report(reps, self.thresholds)

        self.assertIsNone(report["reps"][0]["depth_deg"])
        self.assertIsNone(report["reps"][0]["trunk_lean_deg"])
        self.assertIsNone(report["reps"][0]["asymmetry_pct"])

        depth_row = next(row for row in report["metrics"] if row["key"] == "depth_deg")

        self.assertEqual(depth_row["worst"]["rep"], 2)
        self.assertEqual(depth_row["mean"], 84.0)

    def test_single_rep_has_no_depth_drift(self):
        rep = self.make_rep(
            1,
            {
                "knee_angle": 85.0,
                "trunk_angle": [15.0, 20.0],
                "asymmetry": 5.0,
            },
            {
                "knee_angle": self.classification("acceptable"),
                "trunk_angle": self.classification("acceptable"),
                "asymmetry": self.classification("acceptable"),
            },
        )

        report = build_session_report([rep], self.thresholds)

        self.assertEqual(report["verdict"]["total_reps"], 1)
        self.assertEqual(len(report["reps"]), 1)
        self.assertIsNone(report["trends"]["depth_drift_deg"])
        self.assertIsNone(report["trends"]["velocity_loss_pct"])

    def test_not_evaluated_coverage_is_deduplicated(self):
        classifications = {
            "rom": self.classification(
                "not_evaluated",
                {"reason": "No minimum ROM threshold is configured."},
            ),
            "hip_angle": self.classification(
                "not_evaluated",
                {"reason": "No hip-angle thresholds are configured."},
            ),
            "velocity": self.classification(
                "not_evaluated",
                {"reason": "No velocity thresholds are configured."},
            ),
            "knee_angle": self.classification(
                "not_evaluated",
                {"reason": "Knee angle unavailable."},
            ),
            "trunk_angle": self.classification(
                "not_evaluated",
                {"reason": "Trunk angle unavailable."},
            ),
            "asymmetry": self.classification(
                "not_evaluated",
                {"reason": "Asymmetry unavailable."},
            ),
        }

        reps = [
            self.make_rep(1, {}, classifications),
            self.make_rep(2, {}, classifications),
        ]

        report = build_session_report(reps, self.thresholds)

        self.assertEqual(report["verdict"]["status"], "clean")
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["coverage"]["not_evaluated"]), 6)
        self.assertEqual(
            len(set(report["coverage"]["not_evaluated"])),
            6,
        )
        self.assertEqual(report["reps"][0]["flags"], [])
        self.assertTrue(report["metrics"] == [])
