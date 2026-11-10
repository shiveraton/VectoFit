from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import Profile
from apps.assessments.models import AssessmentSession, RepAssessment
from apps.exercises.models import ExerciseVariant
from apps.datasets.models import (
    Dataset, DatasetAnnotatorAssignment, DatasetSample, DatasetVideo,
    KneeAnnotation, Participant, ViewAngle,
)
from apps.datasets.media_views import signed_dataset_media_url
from rest_framework.test import APIRequestFactory


class AssignmentAccessTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="assigned-rater")
        self.other = User.objects.create_user(username="other-rater")
        for user in (self.user, self.other):
            Profile.objects.create(user=user, is_annotator=True)
        self.client.force_authenticate(self.user)
        participant = Participant.objects.create(participant_code="P-ASSIGN")
        angle, _ = ViewAngle.objects.get_or_create(angle_variant="frontal")
        variant = ExerciseVariant.objects.create(name="Assignment squat", variant_type="BW")
        session = AssessmentSession.objects.create(user=self.user, exercise_variant=variant)
        self.dataset = Dataset.objects.create(
            name="Assigned", exercise_type="bodyweight_squat", purpose="training", status="READY",
        )
        self.video = DatasetVideo.objects.create(
            dataset=self.dataset, participant=participant, view_angle=angle,
            video_file="assignment.mp4", requires_manual_review=True, status="READY",
        )
        rep = RepAssessment.objects.create(session=session, rep_number=1, landmark_series=[])
        self.sample = DatasetSample.objects.create(
            dataset=self.dataset, dataset_video=self.video, rep_assessment=rep,
        )
        self.assignment = DatasetAnnotatorAssignment.objects.create(
            dataset=self.dataset, annotator=self.user,
        )
        self.base = "/api/annotator/"

    def assert_denied(self):
        response = self.client.get(self.base + "datasets/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
        self.assertEqual(self.client.get(self.base + f"datasets/{self.dataset.pk}/session/").status_code, 404)
        self.assertEqual(self.client.get(self.base + f"videos/{self.video.pk}/").status_code, 404)
        response = self.client.patch(self.base + f"samples/{self.sample.pk}/rating/", {"knee_annotation": None}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_unassigned_user_denied_across_all_public_endpoints(self):
        self.client.force_authenticate(self.other)
        self.assert_denied()
        self.assertFalse(KneeAnnotation.objects.exists())

    @patch("apps.annotator.views.cv2.VideoCapture")
    def test_assigned_user_can_list_read_rate_and_access_video(self, capture):
        capture.return_value.get.return_value = 30
        response = self.client.get(self.base + "datasets/")
        self.assertEqual([row["id"] for row in response.data], [self.dataset.pk])
        self.assertEqual(self.client.get(self.base + f"datasets/{self.dataset.pk}/session/").status_code, 200)
        response = self.client.patch(self.base + f"samples/{self.sample.pk}/rating/", {"knee_annotation": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(KneeAnnotation.objects.get().annotator_id, self.user.pk)
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            Path(directory, "assignment.mp4").write_bytes(b"test-video")
            response = self.client.get(self.base + f"videos/{self.video.pk}/")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("X-Accel-Redirect", response)
            self.assertEqual(b"".join(response.streaming_content), b"test-video")
            response.close()

    def test_revocation_denies_all_endpoints_and_preserves_ratings(self):
        record = KneeAnnotation.objects.create(sample=self.sample, annotator=self.user, annotation=None)
        self.assignment.is_active = False
        self.assignment.save(update_fields=["is_active"])
        self.assert_denied()
        self.assertTrue(KneeAnnotation.objects.filter(pk=record.pk).exists())
        self.assignment.is_active = True
        self.assignment.save(update_fields=["is_active"])
        self.assertEqual(len(self.client.get(self.base + "datasets/").data), 1)

    def test_assignment_does_not_override_review_eligibility(self):
        self.video.requires_manual_review = False
        self.video.save(update_fields=["requires_manual_review"])
        self.assert_denied()

    def test_signed_media_honors_active_assignment(self):
        request = APIRequestFactory().get("/", HTTP_HOST="localhost")
        request.user = self.user
        with override_settings(ALLOWED_HOSTS=["localhost"]):
            self.assertIsNotNone(signed_dataset_media_url(request, "dataset-video", self.video.pk, self.dataset))
            request.user = self.other
            self.dataset.all_annotators_access = True
            self.dataset.save(update_fields=["all_annotators_access"])
            self.assertIsNotNone(signed_dataset_media_url(request, "dataset-video", self.video.pk, self.dataset))
            self.other.profile.is_annotator = False
            self.other.profile.save(update_fields=["is_annotator"])
            self.assertIsNone(signed_dataset_media_url(request, "dataset-video", self.video.pk, self.dataset))
            self.other.profile.is_annotator = True
            self.other.profile.save(update_fields=["is_annotator"])
            self.dataset.all_annotators_access = False
            self.dataset.save(update_fields=["all_annotators_access"])
            request.user = self.user
            self.assignment.is_active = False
            self.assignment.save(update_fields=["is_active"])
            self.assertIsNone(signed_dataset_media_url(request, "dataset-video", self.video.pk, self.dataset))

    def test_admin_form_validation_rejects_non_annotator_and_staff(self):
        self.other.profile.is_annotator = False
        self.other.profile.save()
        assignment = DatasetAnnotatorAssignment(dataset=self.dataset, annotator=self.other)
        with self.assertRaises(ValidationError):
            assignment.full_clean()
        self.other.profile.is_annotator = True
        self.other.profile.save()
        self.other.is_staff = True
        self.other.save()
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_public_endpoints_reject_anonymous_and_staff(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.base + "datasets/").status_code, 403)
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(self.base + "datasets/").status_code, 403)
