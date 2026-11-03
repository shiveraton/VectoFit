from io import StringIO
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.roles import ANNOTATOR_GROUP
from apps.assessments.models import AssessmentSession, RepAssessment
from apps.datasets.models import (
    AnnotationEvent,
    Dataset,
    DatasetAnnotatorAssignment,
    DatasetSample,
    KneeAnnotation,
)
from apps.datasets.services.agreement import agreement_for_dataset
from apps.datasets.services.annotation import clear_annotation, save_annotation
from apps.datasets.services.consensus import (
    apply_consensus,
    base_label_for_sample,
    evaluate_sample,
)
from apps.exercises.models import ExerciseVariant


class AnnotationHistoryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.annotator = User.objects.create_user("annotator", password="safe-password")
        self.other = User.objects.create_user("other", password="safe-password")
        self.peer = User.objects.create_user("peer", password="safe-password")
        self.admin = User.objects.create_superuser(
            "admin", "admin@example.com", "safe-password"
        )
        self.group, _ = Group.objects.get_or_create(name=ANNOTATOR_GROUP)
        self.annotator.groups.add(self.group)
        self.peer.groups.add(self.group)
        self.dataset = Dataset.objects.create(
            name="Test", exercise_type="bodyweight_squat", purpose="training"
        )
        variant = ExerciseVariant.objects.create(
            name="Bodyweight Squat",
            variant_type="BW",
            exercise_variant="bodyweight_squat",
        )
        session = AssessmentSession.objects.create(
            user=self.admin, exercise_variant=variant, video_file="test.mp4"
        )
        rep = RepAssessment.objects.create(
            session=session, rep_number=1, landmark_series=[]
        )
        self.sample = DatasetSample.objects.create(
            dataset=self.dataset, rep_assessment=rep
        )
        self.annotation = {
            "left": {"grade": "aligned", "direction": "none"},
            "right": {"grade": "deviated", "direction": "valgus"},
            "symmetry_observation": "asymmetric",
            "notes": "",
        }

    def test_save_identical_save_and_clear_record_provenance(self):
        save_annotation(self.sample, self.annotator, self.annotation)
        save_annotation(self.sample, self.annotator, self.annotation)
        self.assertEqual(AnnotationEvent.objects.filter(action="save").count(), 1)
        clear_annotation(self.sample, self.annotator)
        event = AnnotationEvent.objects.get(action="clear")
        self.assertEqual(event.payload, self.annotation)
        self.assertFalse(KneeAnnotation.objects.filter(sample=self.sample).exists())

    def test_events_are_immutable_but_cascade_with_sample(self):
        save_annotation(self.sample, self.annotator, self.annotation)
        event = AnnotationEvent.objects.first()
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            event.delete()
        with self.assertRaises(TypeError):
            AnnotationEvent.objects.filter(pk=event.pk).update(target_label="bad")
        with self.assertRaises(TypeError):
            AnnotationEvent.objects.filter(pk=event.pk).delete()
        self.sample.delete()
        self.assertFalse(AnnotationEvent.objects.exists())

    def test_admin_can_read_filtered_paginated_history(self):
        save_annotation(self.sample, self.annotator, self.annotation)
        client = APIClient()
        client.force_authenticate(self.admin)
        response = client.get(
            f"/api/datasets/{self.dataset.pk}/annotation-history/",
            {
                "sample": self.sample.pk,
                "annotator": self.annotator.pk,
                "action": "save",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        event = response.data["results"][0]
        self.assertEqual(event["annotator_username"], self.annotator.username)
        self.assertEqual(event["entered_by_username"], self.annotator.username)

    def test_annotator_can_only_patch_own_knee_annotation(self):
        peer_annotation = {**self.annotation, "notes": "private peer note"}
        KneeAnnotation.objects.create(
            sample=self.sample, annotator=self.peer, annotation=peer_annotation
        )
        DatasetAnnotatorAssignment.objects.create(
            dataset=self.dataset, annotator=self.annotator
        )
        client = APIClient()
        client.force_authenticate(self.annotator)
        url = f"/api/datasets/dataset-samples/{self.sample.pk}/"
        response = client.patch(
            url, {"knee_annotation": self.annotation}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["knee_annotation"], self.annotation)
        self.assertEqual(AnnotationEvent.objects.filter(action="save").count(), 1)
        client.force_authenticate(self.other)
        response = client.get(f"/api/datasets/{self.dataset.pk}/annotation/")
        self.assertEqual(response.status_code, 403)
        client.force_authenticate(self.annotator)
        response = client.get(f"/api/datasets/{self.dataset.pk}/annotation/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["samples"][0]["knee_annotation"], self.annotation
        )
        self.assertNotEqual(
            response.data["samples"][0]["knee_annotation"], peer_annotation
        )
        response = client.get("/api/datasets/annotation-queue/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["annotated_by_me"], 1)
        self.assertEqual(response.data[0]["pending_for_me"], 0)
        response = client.patch(url, {"is_correct": True}, format="json")
        self.assertEqual(response.status_code, 403)
        response = client.patch(url, {"unexpected": True}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_annotator_is_denied_admin_operations_and_audit_endpoints(self):
        client = APIClient()
        client.force_authenticate(self.annotator)
        paths = [
            ("post", "/api/datasets/", {}),
            ("delete", f"/api/datasets/{self.dataset.pk}/", None),
            ("post", f"/api/datasets/{self.dataset.pk}/retry/", {}),
            ("get", "/api/datasets/participant/", None),
            ("get", "/api/datasets/view-angle/", None),
            ("get", "/api/datasets/dataset-videos/", None),
            ("get", "/api/training/jobs/", None),
            ("get", "/api/training/models/", None),
            ("get", f"/api/datasets/{self.dataset.pk}/annotation-history/", None),
            ("get", f"/api/datasets/{self.dataset.pk}/consensus/", None),
            ("get", f"/api/datasets/{self.dataset.pk}/agreement/", None),
            ("post", "/api/datasets/import/", {}),
        ]
        for method, path, data in paths:
            response = (
                getattr(client, method)(path, data, format="json")
                if data is not None
                else getattr(client, method)(path)
            )
            self.assertEqual(
                response.status_code, 403, f"{method.upper()} {path}: {response.data}"
            )

    def test_consensus_majority_and_adjudication_protection(self):
        good = {
            "left": {"grade": "aligned", "direction": "none"},
            "right": {"grade": "aligned", "direction": "none"},
            "symmetry_observation": "symmetric",
            "notes": "",
        }
        KneeAnnotation.objects.create(
            sample=self.sample, annotator=self.annotator, annotation=good
        )
        result = evaluate_sample(self.sample)
        self.assertEqual(result["status"], "insufficient")
        KneeAnnotation.objects.create(
            sample=self.sample, annotator=self.peer, annotation=good
        )
        result = evaluate_sample(self.sample)
        self.assertEqual(result["status"], "resolved")
        apply_consensus(self.sample, result)
        self.sample.refresh_from_db()
        self.assertTrue(self.sample.is_correct)
        self.assertEqual(self.sample.label_source, "consensus")
        self.sample.label_source = "adjudicated"
        self.sample.is_correct = False
        self.sample.save(update_fields=["label_source", "is_correct"])
        apply_consensus(self.sample, result)
        self.sample.refresh_from_db()
        self.assertFalse(self.sample.is_correct)
        self.assertEqual(self.sample.label_source, "adjudicated")
        self.sample.label_source = ""
        self.sample.save(update_fields=["label_source"])
        borderline = {
            "left": {"grade": "borderline", "direction": "uncertain"},
            "right": {"grade": "borderline", "direction": "uncertain"},
            "symmetry_observation": "uncertain",
            "notes": "",
        }
        KneeAnnotation.objects.filter(sample=self.sample).update(annotation=borderline)
        self.assertEqual(evaluate_sample(self.sample)["status"], "not_trainable")
        bad = {
            "left": {"grade": "deviated", "direction": "valgus"},
            "right": {"grade": "deviated", "direction": "valgus"},
            "symmetry_observation": "asymmetric",
            "notes": "",
        }
        KneeAnnotation.objects.filter(sample=self.sample, annotator=self.peer).update(
            annotation=bad
        )
        self.assertEqual(evaluate_sample(self.sample)["status"], "disagreement")

    def test_consensus_rejects_invalid_status_and_label_combinations(self):
        malformed_results = [
            {"status": "unknown", "label": None, "labels": {}},
            {"status": "resolved", "label": "borderline", "labels": {}},
            {"status": "not_trainable", "label": "good", "labels": {}},
            {"status": "insufficient", "label": "bad", "labels": {}},
            {"status": "disagreement", "label": None, "labels": {"1": "unknown"}},
            {"status": "resolved", "label": "good", "labels": []},
        ]
        for result in malformed_results:
            with self.subTest(result=result), self.assertRaises(ValueError):
                apply_consensus(self.sample, result)
        self.sample.refresh_from_db()
        self.assertIsNone(self.sample.is_correct)
        self.assertEqual(self.sample.label_source, "")

    def test_consensus_force_only_overrides_adjudicated_protection(self):
        resolved = {"status": "resolved", "label": "bad", "labels": {}}
        self.sample.is_correct = True
        self.sample.label_source = "adjudicated"
        self.sample.save(update_fields=["is_correct", "label_source"])

        self.assertFalse(apply_consensus(self.sample, resolved))
        self.sample.refresh_from_db()
        self.assertTrue(self.sample.is_correct)
        self.assertEqual(self.sample.label_source, "adjudicated")

        self.assertTrue(apply_consensus(self.sample, resolved, force=True))
        self.sample.refresh_from_db()
        self.assertFalse(self.sample.is_correct)
        self.assertEqual(self.sample.label_source, "consensus")

    def test_force_with_nonresolved_result_clears_adjudication(self):
        self.sample.is_correct = True
        self.sample.label_source = "adjudicated"
        self.sample.save(update_fields=["is_correct", "label_source"])
        result = {"status": "insufficient", "label": None, "labels": {}}

        self.assertTrue(apply_consensus(self.sample, result, force=True))
        self.sample.refresh_from_db()
        self.assertIsNone(self.sample.is_correct)
        self.assertEqual(self.sample.label_source, "")

    def test_force_must_be_a_bool(self):
        result = {"status": "insufficient", "label": None, "labels": {}}
        with self.assertRaises(ValueError):
            apply_consensus(self.sample, result, force=1)

    def test_source_label_is_bool_or_none(self):
        sample = SimpleNamespace(
            dataset_video=SimpleNamespace(
                source_label="false", requires_manual_review=False
            )
        )
        with self.assertRaisesRegex(ValueError, "bool or None"):
            base_label_for_sample(sample)

    def test_agreement_reports_cohen_and_fleiss_values(self):
        grades_a = ["aligned", "aligned", "deviated", "deviated"]
        grades_b = ["aligned", "deviated", "deviated", "deviated"]
        samples = [self.sample]
        for rep_number in range(2, 5):
            rep = RepAssessment.objects.create(
                session=self.sample.rep_assessment.session,
                rep_number=rep_number,
                landmark_series=[],
            )
            samples.append(
                DatasetSample.objects.create(dataset=self.dataset, rep_assessment=rep)
            )
        for sample, grade_a, grade_b in zip(samples, grades_a, grades_b):
            for user, grade in ((self.annotator, grade_a), (self.peer, grade_b)):
                annotation = {
                    "left": {"grade": grade, "direction": "none"},
                    "right": {"grade": grade, "direction": "none"},
                    "symmetry_observation": "symmetric",
                    "notes": "",
                }
                KneeAnnotation.objects.create(
                    sample=sample, annotator=user, annotation=annotation
                )
        result = agreement_for_dataset(self.dataset)
        for field in ("target_label", "left.grade", "right.grade"):
            self.assertAlmostEqual(result[field]["observed_agreement"], 0.75)
            self.assertAlmostEqual(result[field]["pairwise_cohen_kappa"], 0.5)
            self.assertAlmostEqual(result[field]["fleiss_kappa"], 0.4666666667)
            self.assertEqual(result[field]["fleiss_excluded_samples"], 0)

    def test_reassign_orphans_honors_dry_run_and_existing_records(self):
        orphan = KneeAnnotation.objects.create(
            sample=self.sample, annotator=None, annotation=self.annotation
        )
        output = StringIO()
        call_command(
            "reassign_orphan_annotations",
            username=self.annotator.username,
            dry_run=True,
            stdout=output,
        )
        orphan.refresh_from_db()
        self.assertIsNone(orphan.annotator_id)
        call_command(
            "reassign_orphan_annotations",
            username=self.annotator.username,
            stdout=StringIO(),
        )
        orphan.refresh_from_db()
        self.assertEqual(orphan.annotator_id, self.annotator.pk)
        self.assertEqual(AnnotationEvent.objects.filter(action="reassign").count(), 1)

        other_sample_rep = RepAssessment.objects.create(
            session=self.sample.rep_assessment.session,
            rep_number=2,
            landmark_series=[],
        )
        other_sample = DatasetSample.objects.create(
            dataset=self.dataset, rep_assessment=other_sample_rep
        )
        existing = KneeAnnotation.objects.create(
            sample=other_sample, annotator=self.annotator, annotation=self.annotation
        )
        skipped = KneeAnnotation.objects.create(
            sample=other_sample, annotator=None, annotation=self.annotation
        )
        call_command(
            "reassign_orphan_annotations",
            username=self.annotator.username,
            stdout=StringIO(),
        )
        skipped.refresh_from_db()
        self.assertIsNone(skipped.annotator_id)
        self.assertIsNotNone(existing.pk)
