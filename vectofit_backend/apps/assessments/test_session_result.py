from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.analytics.services.fppa import evaluate_fppa
from apps.exercises.models import ExerciseVariant
from .models import AssessmentSession, RepAssessment
from .services.session_result import build_session_result


class SessionResultTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("result-user", password="test-pass")
        self.other = User.objects.create_user("other-result-user", password="test-pass")
        self.variant = ExerciseVariant.objects.create(name="Bodyweight", exercise_variant="Bodyweight", variant_type="BW")
        self.session = AssessmentSession.objects.create(user=self.user, exercise_variant=self.variant,
            view_angle="frontal", status="COMPLETED", capture_mirrored=True)
        self.client.force_authenticate(self.user)

    def rep(self, index=1, left=3, right=-14, model="bad", session=None):
        fppa = evaluate_fppa({"fppa_l_peak": left, "fppa_r_peak": right})
        fppa["trace"] = {"left": [1, left, 2], "right": [-1, right, -2]}
        points = {name: [100, 100] for name in ["nose", "left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"]}
        entries = [{"timestamp_ms": time, "frame_index": i, "source_width": 400, "source_height": 600,
            "native_fps": 30, "landmarks": points} for i, time in enumerate([1000, 1500, 2000])]
        return RepAssessment.objects.create(session=session or self.session, rep_number=index, landmark_series=entries,
            analysis_result={"fppa": fppa, "model_prediction": {"status": "assessed", "prediction_target": "knee_alignment",
                "view_angle": "frontal", "predicted_class": model, "probability": 0.82}})

    def test_result_preserves_signed_angles_real_timing_and_normalized_frames(self):
        self.rep()
        result = build_session_result(self.session)
        rep = result["reps"][0]
        self.assertEqual(rep["worstPeakDeg"], -14)
        self.assertEqual(rep["kneeDirection"]["right"], "outward")
        self.assertEqual(rep["peakAtMs"], 500)
        self.assertEqual(rep["series"]["tMs"], [0, 500, 1000])
        self.assertEqual(rep["frames"][0]["pts"]["nose"], [0.25, 1 / 6])
        self.assertEqual(result["summary"]["balanceDeg"], 11)
        self.assertIn("outward", result["presentation"]["headline"])
        self.assertEqual(rep["phases"], None)

    def test_invalid_measurements_are_excluded_and_no_borderline_threshold_is_added(self):
        self.rep(1, 3, 4, "good")
        RepAssessment.objects.create(session=self.session, rep_number=2, landmark_series=[], analysis_result={})
        result = build_session_result(self.session)
        self.assertEqual(result["summary"]["counts"], {"aligned": 1, "borderline": 0, "deviated": 0, "unassessable": 1})
        self.assertEqual(result["summary"]["assessableReps"], 1)
        self.assertEqual(result["summary"]["right"]["worstPeakDeg"], 4)

    def test_unknown_mirroring_never_produces_a_skeleton(self):
        self.rep()
        self.session.capture_mirrored = None
        result = build_session_result(self.session)
        self.assertIsNone(result["capture"]["mirrored"])
        self.assertIsNone(result["reps"][0]["frames"])
        self.assertIsNotNone(result["reps"][0]["series"])

    def test_missing_measurement_and_invalid_model_confidence_stay_unavailable(self):
        rep = self.rep()
        rep.analysis_result["fppa"] = None
        rep.analysis_result["model_prediction"]["probability"] = 1.5
        rep.save()
        result = build_session_result(self.session)["reps"][0]
        self.assertEqual(result["status"], "unassessable")
        self.assertIsNone(result["peakDeg"])
        self.assertEqual(result["modelEvidence"], {"label": None, "confidence": None, "disagrees": None})

    def test_model_disagreement_is_preserved_and_suppresses_corrective_cues(self):
        self.rep(model="good")
        result = build_session_result(self.session)
        self.assertTrue(result["reps"][0]["modelEvidence"]["disagrees"])
        self.assertTrue(result["presentation"]["modelDisagreement"])
        self.assertEqual(result["presentation"]["cues"], [])
        self.assertEqual(result["reps"][0]["status"], "deviated")

    def test_missing_samples_are_not_bridged_or_replaced_with_a_new_peak(self):
        rep = self.rep()
        rep.analysis_result["fppa"]["trace"]["left"][1] = None
        rep.save()
        self.assertIsNone(build_session_result(self.session)["reps"][0]["series"])
        rep.analysis_result["fppa"]["trace"]["left"] = [1, 9, 2]
        rep.save()
        self.assertIsNone(build_session_result(self.session)["reps"][0]["series"])
        self.assertEqual(build_session_result(self.session)["reps"][0]["peakDeg"]["left"], 3)

    def test_previous_comparison_is_owned_and_exercise_specific(self):
        previous = AssessmentSession.objects.create(user=self.user, exercise_variant=self.variant, view_angle="frontal", status="COMPLETED")
        AssessmentSession.objects.filter(pk=previous.pk).update(created_at=self.session.created_at - timedelta(days=1))
        self.rep(session=previous, left=2, right=3, model="good")
        other = AssessmentSession.objects.create(user=self.other, exercise_variant=self.variant, view_angle="frontal", status="COMPLETED")
        AssessmentSession.objects.filter(pk=other.pk).update(created_at=self.session.created_at - timedelta(hours=1))
        self.rep(session=other)
        self.assertEqual(build_session_result(self.session)["summary"]["previousAlignedCount"], 1)

    def test_detail_endpoint_extends_existing_contract_and_rejects_other_owners(self):
        self.rep()
        url = reverse("assessment-session-detail", args=[self.session.pk])
        response = self.client.get(url, {"include": "reps"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session_result"]["sessionId"], str(self.session.pk))
        self.assertIn("reps", response.data)
        self.assertNotIn("session_result", self.client.get(url).data)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(url, {"include": "reps"}).status_code, 404)

    @patch("apps.assessments.views._enqueue_assessment_processing")
    def test_existing_retry_endpoint_moves_only_failed_owned_sessions_to_pending(self, enqueue):
        self.session.status = "FAILED"
        self.session.save()
        url = reverse("assessment-session-retry", args=[self.session.pk])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url)
        self.assertEqual(response.status_code, 202)
        enqueue.assert_called_once_with(self.session.pk)
        self.assertEqual(self.client.post(url).status_code, 409)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(url).status_code, 404)
