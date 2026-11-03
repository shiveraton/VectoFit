from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.roles import annotator_group
from apps.assessments.models import AssessmentSession, RepAssessment
from apps.datasets.models import Dataset, DatasetAnnotatorAssignment, DatasetSample
from apps.exercises.models import ExerciseVariant


class AnnotatorAssignmentAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            "admin", "admin@example.com", "admin-pass-9812"
        )
        self.annotator = User.objects.create_user(
            "annotator", password="annotator-pass-9812"
        )
        self.annotator.groups.add(annotator_group())

        self.assigned = Dataset.objects.create(
            name="Assigned", exercise_type="bodyweight_squat", purpose="training"
        )
        self.unassigned = Dataset.objects.create(
            name="Hidden", exercise_type="bodyweight_squat", purpose="training"
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
        DatasetSample.objects.create(dataset=self.assigned, rep_assessment=rep)
        DatasetSample.objects.create(dataset=self.unassigned, rep_assessment=rep)

    def test_annotator_only_reaches_assigned_datasets(self):
        client = APIClient()
        client.force_authenticate(self.annotator)

        self.assertEqual(
            client.get(f"/api/datasets/{self.assigned.pk}/annotation/").status_code,
            404,
            "unassigned annotators must not open a dataset",
        )

        DatasetAnnotatorAssignment.objects.create(
            dataset=self.assigned, annotator=self.annotator
        )

        self.assertEqual(
            client.get(f"/api/datasets/{self.assigned.pk}/annotation/").status_code,
            200,
        )
        self.assertEqual(
            client.get(f"/api/datasets/{self.unassigned.pk}/annotation/").status_code,
            404,
        )

    def test_annotation_queue_lists_assigned_datasets_with_status(self):
        DatasetAnnotatorAssignment.objects.create(
            dataset=self.assigned, annotator=self.annotator
        )
        client = APIClient()
        client.force_authenticate(self.annotator)

        response = client.get("/api/datasets/annotation-queue/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["name"] for row in response.data], ["Assigned"])
        self.assertIn("status", response.data[0])
        self.assertEqual(response.data[0]["review_total"], 1)

    def test_inactive_assignment_removes_access(self):
        DatasetAnnotatorAssignment.objects.create(
            dataset=self.assigned, annotator=self.annotator, is_active=False
        )
        client = APIClient()
        client.force_authenticate(self.annotator)

        response = client.get("/api/datasets/annotation-queue/")

        self.assertEqual(response.data, [])

    def test_admin_bulk_assign_creates_then_reactivates(self):
        client = APIClient()
        client.force_authenticate(self.admin)

        response = client.post(
            "/api/datasets/annotator-assignments/bulk/",
            {"dataset": self.assigned.pk, "annotators": [self.annotator.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(response.data["total"], 1)

        assignment = DatasetAnnotatorAssignment.objects.get(
            dataset=self.assigned, annotator=self.annotator
        )
        self.assertTrue(assignment.is_active)
        self.assertEqual(assignment.assigned_by, self.admin)

        assignment.is_active = False
        assignment.save(update_fields=["is_active"])

        response = client.post(
            "/api/datasets/annotator-assignments/bulk/",
            {"dataset": self.assigned.pk, "annotators": [self.annotator.pk]},
            format="json",
        )
        self.assertEqual(response.data["created"], 0)
        self.assertEqual(response.data["reactivated"], 1)
        assignment.refresh_from_db()
        self.assertTrue(assignment.is_active)

    def test_bulk_assign_rejects_non_annotators_and_missing_dataset(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        other = get_user_model().objects.create_user("plain", password="plain-pass-9812")

        response = client.post(
            "/api/datasets/annotator-assignments/bulk/",
            {"dataset": self.assigned.pk, "annotators": [other.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("annotators", response.data)

        response = client.post(
            "/api/datasets/annotator-assignments/bulk/",
            {"annotators": [self.annotator.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        response = client.post(
            "/api/datasets/annotator-assignments/bulk/",
            {"dataset": 999999, "annotators": [self.annotator.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_unassign_removes_the_record(self):
        DatasetAnnotatorAssignment.objects.create(
            dataset=self.assigned, annotator=self.annotator
        )
        client = APIClient()
        client.force_authenticate(self.admin)

        response = client.post(
            "/api/datasets/annotator-assignments/unassign/",
            {"dataset": self.assigned.pk, "annotator": self.annotator.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(DatasetAnnotatorAssignment.objects.exists())

    def test_annotator_cannot_manage_assignments(self):
        client = APIClient()
        client.force_authenticate(self.annotator)

        response = client.post(
            "/api/datasets/annotator-assignments/",
            {"dataset": self.unassigned.pk, "annotator": self.annotator.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(DatasetAnnotatorAssignment.objects.exists())
