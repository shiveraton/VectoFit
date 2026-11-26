import io
import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from apps.annotator import tests as annotator_tests
from .models import Dataset, DatasetSample, KneeAnnotation


def rating(left="aligned", right="aligned"):
    return {"left": {"grade": left, "direction": "uncertain"},
            "right": {"grade": right, "direction": "uncertain"}, "notes": ""}


class BinaryRubricTests(APITestCase):
    setUp = annotator_tests.AssignmentAccessTests.setUp

    def test_annotation_api_accepts_only_binary_grades_and_versions_new_ratings(self):
        url = self.base + f"samples/{self.sample.pk}/rating/"
        for grade in ("borderline", "unassessable"):
            self.assertEqual(self.client.patch(url, {"knee_annotation": rating(grade)}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"knee_annotation": rating("deviated")}, format="json").status_code, 200)
        self.assertEqual(KneeAnnotation.objects.get().rubric_version, "knee_binary_v1")

    def test_database_rejects_retired_grades_for_binary_rubric(self):
        for grade in ("borderline", "unassessable", None):
            with self.subTest(grade=grade), self.assertRaises(IntegrityError), transaction.atomic():
                KneeAnnotation.objects.create(sample=self.sample, annotator=self.user, annotation=rating(grade))

    def test_reset_backs_up_and_only_removes_selected_dataset_and_annotator(self):
        original = KneeAnnotation.objects.create(sample=self.sample, annotator=self.user, annotation=rating())
        other_rater = KneeAnnotation.objects.create(sample=self.sample, annotator=self.other, annotation=rating())
        other_dataset = Dataset.objects.create(name="Other", exercise_type="bodyweight_squat", purpose="training")
        other_sample = DatasetSample.objects.create(dataset=other_dataset, rep_assessment=self.sample.rep_assessment)
        outside = KneeAnnotation.objects.create(sample=other_sample, annotator=self.user, annotation=rating())
        self.sample.annotator = self.user
        self.sample.is_correct = True
        self.sample.save(update_fields=["annotator", "is_correct"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.json"
            call_command("reset_dataset_annotations", dataset_id=self.dataset.pk, annotator_id=self.user.pk,
                         backup=str(path), stdout=io.StringIO())
            backup = json.loads(path.read_text())
            self.assertEqual([r["id"] for r in backup["knee_annotations"]], [original.pk])
        self.assertFalse(KneeAnnotation.objects.filter(pk=original.pk).exists())
        self.assertEqual(set(KneeAnnotation.objects.values_list("pk", flat=True)), {other_rater.pk, outside.pk})
        self.sample.refresh_from_db()
        self.assertIsNone(self.sample.is_correct)
        self.assertIsNone(self.sample.annotator_id)
