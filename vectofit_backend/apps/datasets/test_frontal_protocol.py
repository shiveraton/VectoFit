from types import SimpleNamespace
from io import StringIO
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.annotator import tests as annotator_tests
from apps.datasets.models import DatasetSample, DatasetVideo, KneeAnnotation, ViewAngle
from apps.datasets.services.knee_label import knee_target
from apps.training.services.data_loader import (
    FrameTimingError, prepare_knee_samples, build_samples,
)
from apps.training.services.run_training_job import _build_manifest


def rating(left="aligned", right="aligned"):
    return {"left": {"grade": left, "direction": "uncertain"},
            "right": {"grade": right, "direction": "uncertain"},
            "notes": ""}


class FrontalProtocolTests(APITestCase):
    setUp = annotator_tests.AssignmentAccessTests.setUp

    def annotate(self, value=None, user=None):
        return KneeAnnotation.objects.create(sample=self.sample, annotator=user or self.user,
                                             annotation=value if value is not None else rating())

    def prepare(self):
        return prepare_knee_samples([self.dataset])

    def assert_exclusion(self, reason):
        report = self.prepare().readiness_report()
        self.assertEqual(report["exclusion_counts"], {reason: 1})
        self.assertEqual(report["inspected_count"], report["eligible_count"] + report["excluded_count"])
        self.assertTrue(report["training_blockers"])

    def test_incomplete_values_never_become_good(self):
        for value in ({}, None, rating(None), rating("deviated", None), rating([], "aligned")):
            with self.subTest(value=value):
                self.assertEqual(knee_target(value), "incomplete")
        self.assertEqual(knee_target(rating("deviated", "unassessable")), "bad")
        self.assertEqual(knee_target(rating("borderline", "unassessable")), "unassessable")

    @patch("apps.datasets.views.cv2.VideoCapture")
    def test_non_frontal_queues_counts_and_writes(self, capture):
        admin = get_user_model().objects.create_user(username="frontal-admin", is_staff=True)
        for angle in ("diagonal", "sagittal"):
            self.video.view_angle = ViewAngle.objects.get_or_create(angle_variant=angle)[0]
            self.video.save(update_fields=["view_angle"])
            self.assertEqual(self.client.get(self.base + "datasets/").data, [])
            self.assertEqual(self.client.patch(self.base + f"samples/{self.sample.pk}/rating/",
                {"knee_annotation": rating()}, format="json").status_code, 400)
            self.client.force_authenticate(admin)
            response = self.client.patch(f"/api/datasets/dataset-samples/{self.sample.pk}/",
                {"knee_annotation": rating()}, format="json")
            self.assertEqual(response.status_code, 400)
            pool = self.client.get("/api/datasets/annotation-pool/")
            self.assertEqual(pool.data[0]["sample_count"], 0)
            self.client.force_authenticate(self.user)
        self.assertEqual(KneeAnnotation.objects.count(), 0)

    def test_both_annotation_apis_reject_missing_grades(self):
        for url in (self.base + f"samples/{self.sample.pk}/rating/",
                    f"/api/datasets/dataset-samples/{self.sample.pk}/"):
            response = self.client.patch(url, {"knee_annotation": rating(None)}, format="json")
            self.assertEqual(response.status_code, 400)

    @patch("apps.annotator.views.resolved_video_path", side_effect=OSError)
    def test_mixed_angle_queue_keeps_only_frontal_and_audit_is_read_only(self, media):
        other_video = DatasetVideo.objects.create(
            dataset=self.dataset, participant=self.video.participant,
            view_angle=ViewAngle.objects.get_or_create(angle_variant="diagonal")[0],
            status="READY", requires_manual_review=True, video_file="diagonal.mp4",
        )
        DatasetSample.objects.create(dataset=self.dataset, dataset_video=other_video,
                                     rep_assessment=self.sample.rep_assessment)
        response = self.client.get(self.base + f"datasets/{self.dataset.pk}/session/")
        self.assertEqual([row["id"] for row in response.data["samples"]], [self.sample.pk])
        self.assertEqual(response.data["dataset"]["sample_count"], 1)
        output = StringIO()
        call_command("audit_knee_readiness", dataset_ids=[self.dataset.pk], stdout=output)
        report = json.loads(output.getvalue())
        self.assertEqual(report["inspected_count"], 2)
        self.assertEqual(report["exclusion_counts"], {"non_frontal_view": 1, "missing_annotation": 1})
        self.assertEqual(KneeAnnotation.objects.count(), 0)
        self.assertEqual(DatasetSample.objects.count(), 2)

    @patch("apps.datasets.views.cv2.VideoCapture")
    def test_legacy_angle_is_used_only_without_video(self, capture):
        self.dataset.view_angle = ViewAngle.objects.get_or_create(angle_variant="frontal")[0]
        self.dataset.save(update_fields=["view_angle"])
        self.video.view_angle = ViewAngle.objects.get_or_create(angle_variant="diagonal")[0]
        self.video.save(update_fields=["view_angle"])
        self.assert_exclusion("non_frontal_view")
        self.sample.dataset_video = None
        self.sample.save(update_fields=["dataset_video"])
        response = self.client.get(self.base + f"datasets/{self.dataset.pk}/session/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["samples"][0]["dataset_video"])
        self.assertEqual(response.data["samples"][0]["view_angle_name"], "frontal")
        self.dataset.view_angle = None
        self.dataset.save(update_fields=["view_angle"])
        response = self.client.patch(self.base + f"samples/{self.sample.pk}/rating/",
            {"knee_annotation": rating()}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_diagnostic_precedence_and_zero_eligible_report(self):
        self.assert_exclusion("missing_annotation")
        self.annotate(rating(None))
        self.assert_exclusion("incomplete_annotation")
        self.annotate(rating("borderline"))
        self.assert_exclusion("borderline")
        self.annotate(rating("unassessable"))
        self.assert_exclusion("unassessable")
        self.annotate()
        self.annotate(rating("deviated"), self.other)
        self.assert_exclusion("disputed")
        self.annotate(user=self.other)
        self.assert_exclusion("missing_landmark_data")
        self.sample.rep_assessment.landmark_series = [{"left_knee": [1, 2]}]
        self.sample.rep_assessment.save(update_fields=["landmark_series"])
        self.assert_exclusion("insufficient_frames")

    def test_provenance_and_readiness_permissions(self):
        KneeAnnotation.objects.create(sample=self.sample, annotation=rating())
        self.assert_exclusion("missing_human_provenance")
        url = f"/api/datasets/{self.dataset.pk}/knee-readiness/"
        self.assertEqual(self.client.get(url).status_code, 403)
        admin = get_user_model().objects.create_user(username="readiness-admin", is_staff=True)
        self.client.force_authenticate(admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["eligible_count"], 0)

    def test_empty_dataset(self):
        self.sample.delete()
        report = self.prepare().readiness_report()
        self.assertEqual(report["inspected_count"], 0)
        self.assertEqual(report["exclusions"], [])

    def test_timing_and_extraction_failures_are_distinct(self):
        self.annotate()
        rep = self.sample.rep_assessment
        rep.landmark_series = [{"left_knee": [1, 2]}] * 3
        rep.save(update_fields=["landmark_series"])
        for error, reason in ((FrameTimingError("bad timing"), "invalid_timing"),
                              (ValueError("bad features"), "feature_extraction_failure")):
            with patch("apps.training.services.data_loader._extract_sample_features", side_effect=error):
                self.assert_exclusion(reason)

    def test_preparation_training_and_manifest_use_same_evidence(self):
        self.annotate()
        rep = self.sample.rep_assessment
        rep.landmark_series = [{"left_knee": [1, 2]}] * 3
        rep.save(update_fields=["landmark_series"])
        second = DatasetSample.objects.create(dataset=self.dataset, dataset_video=self.video, rep_assessment=rep)
        KneeAnnotation.objects.create(sample=second, annotator=self.user, annotation=rating("deviated"))
        with patch("apps.training.services.data_loader._extract_sample_features", return_value=({}, {}, "frame_timestamps")), \
             patch("apps.training.services.data_loader.to_feature_row", return_value=[1.0] * 6):
            prepared = self.prepare()
            trained = build_samples([self.dataset], [], view_angle="frontal", prediction_target="knee_alignment")
        self.assertEqual(prepared.sample_ids, trained.sample_ids)
        self.assertEqual(prepared.readiness_report()["class_counts"], {"good": 1, "bad": 1})
        job = SimpleNamespace(pk=1, feature_schema_version="fppa_v2", algorithm="xgboost")
        result = {"train_idx": [0], "test_idx": [1], "hyperparameters": {},
                  "class_mapping": {}, "target_names": [], "metrics": {}}
        with patch("apps.training.services.run_training_job.timezone.now") as now:
            now.return_value.isoformat.return_value = "fixed"
            first = _build_manifest(job, [self.dataset], trained, result, "frontal", "knee_alignment", .3, 42)
            trained.eligibility_policy_version = "changed"
            changed = _build_manifest(job, [self.dataset], trained, result, "frontal", "knee_alignment", .3, 42)
            self.assertNotEqual(first["manifest_sha256"], changed["manifest_sha256"])
            trained.annotation_evidence[0]["annotations"][0]["annotation"]["notes"] = "updated"
            annotated = _build_manifest(job, [self.dataset], trained, result, "frontal", "knee_alignment", .3, 42)
            self.assertNotEqual(changed["manifest_sha256"], annotated["manifest_sha256"])
