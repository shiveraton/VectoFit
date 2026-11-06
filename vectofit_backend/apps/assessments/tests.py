from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from tempfile import TemporaryDirectory
from unittest.mock import patch

from apps.exercises.models import ExerciseVariant

from .models import AssessmentSession, BodyProfile, RepAssessment

User = get_user_model()


class BodyProfileModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jhed", password="pass12345")

    def test_str_includes_username(self):
        profile = BodyProfile.objects.create(
            user=self.user,
            height_cm=170,
            torso_length_cm=55,
            femur_length_cm=45,
            tibia_length_cm=40,
            scale_factor=1.02,
        )
        self.assertIn(self.user.username, str(profile))


class AssessmentSessionAPITests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="jhed", password="pass12345")
        self.other_user = User.objects.create_user(
            username="other", password="pass12345"
        )
        self.variant = ExerciseVariant.objects.create(
            exercise_variant="Bodyweight Squat",
            name="Bodyweight Squat",
            variant_type=ExerciseVariant.VariantType.BODYWEIGHT,
        )
        self.client.force_authenticate(self.user)

    def test_session_list_scoped_to_requesting_user(self):
        AssessmentSession.objects.create(user=self.user, exercise_variant=self.variant)
        AssessmentSession.objects.create(
            user=self.other_user, exercise_variant=self.variant
        )

        response = self.client.get(reverse("assessment-session-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("assessment-session-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_uses_detail_serializer_with_reps(self):
        session = AssessmentSession.objects.create(
            user=self.user,
            exercise_variant=self.variant,
        )

        RepAssessment.objects.create(
            session=session,
            rep_number=1,
            landmark_series=[],
        )

        url = reverse(
            "assessment-session-detail",
            args=[session.pk],
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("reps", response.data)
        self.assertIn("report", response.data)

        response = self.client.get(url, {"include": "reps"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("reps", response.data)
        self.assertEqual(len(response.data["reps"]), 1)

    def test_rep_assessment_api_is_read_only_and_user_scoped(self):
        own_session = AssessmentSession.objects.create(
            user=self.user,
            exercise_variant=self.variant,
        )
        other_session = AssessmentSession.objects.create(
            user=self.other_user,
            exercise_variant=self.variant,
        )
        own_rep = RepAssessment.objects.create(
            session=own_session,
            rep_number=1,
            jaa_score=0.5,
            landmark_series=[],
        )
        other_rep = RepAssessment.objects.create(
            session=other_session,
            rep_number=1,
            jaa_score=0.25,
            landmark_series=[],
        )

        response = self.client.patch(
            reverse("rep-assessment-detail", args=[own_rep.pk]),
            {"jaa_score": 1.0},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        own_rep.refresh_from_db()
        self.assertEqual(own_rep.jaa_score, 0.5)

        response = self.client.get(reverse("rep-assessment-detail", args=[other_rep.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assessment_processing_is_queued_after_commit(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            with patch("apps.assessments.tasks.process_assessment_session.delay") as delay:
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(
                        reverse("assessment-session-list"),
                        {
                            "exercise_variant": self.variant.pk,
                            "view_angle": "frontal",
                            "video_file": SimpleUploadedFile(
                                "squat.mp4", b"video", content_type="video/mp4"
                            ),
                        },
                        format="multipart",
                    )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        delay.assert_called_once_with(response.data["id"])
        session = AssessmentSession.objects.get(pk=response.data["id"])
        self.assertEqual(session.status, AssessmentSession.Status.PENDING)

    def test_task_failure_marks_session_failed_and_retryable(self):
        session = AssessmentSession.objects.create(
            user=self.user,
            exercise_variant=self.variant,
            status=AssessmentSession.Status.PENDING,
        )
        with patch(
            "apps.assessments.tasks.run_assessment_processing",
            side_effect=RuntimeError("worker error"),
        ):
            from .tasks import process_assessment_session

            result = process_assessment_session.run(session.pk)

        session.refresh_from_db()
        self.assertEqual(result, AssessmentSession.Status.FAILED)
        self.assertEqual(session.status, AssessmentSession.Status.FAILED)
        self.assertIn("worker error", session.error_message)
        self.assertIsNotNone(session.processed_at)

    def test_failed_assessment_can_be_requeued_after_commit(self):
        session = AssessmentSession.objects.create(
            user=self.user,
            exercise_variant=self.variant,
            status=AssessmentSession.Status.FAILED,
            error_message="previous failure",
        )
        with patch("apps.assessments.tasks.process_assessment_session.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("assessment-session-retry", args=[session.pk]),
                    {},
                    format="json",
                )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        delay.assert_called_once_with(session.pk)
        session.refresh_from_db()
        self.assertEqual(session.status, AssessmentSession.Status.PENDING)
        self.assertEqual(session.error_message, "")


class RepAssessmentModelTests(APITestCase):
    @classmethod
    def setUp(self):
        self.user = User.objects.create_user(username="jhed", password="pass12345")
        self.other_user = User.objects.create_user(
            username="other", password="pass12345"
        )
        self.variant = ExerciseVariant.objects.create(
            exercise_variant="Goblet Squat",
            name="Goblet Squat",
            variant_type=ExerciseVariant.VariantType.GOBLET,
        )
        self.session = AssessmentSession.objects.create(
            user=self.user, exercise_variant=self.variant
        )

    def test_rep_number_unique_per_session(self):
        RepAssessment.objects.create(
            session=self.session, rep_number=1, landmark_series=[]
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RepAssessment.objects.create(
                session=self.session, rep_number=1, landmark_series=[]
            )

    def test_same_rep_number_allowed_across_different_sessions(self):
        other_session = AssessmentSession.objects.create(
            user=self.user, exercise_variant=self.variant
        )
        RepAssessment.objects.create(
            session=self.session, rep_number=1, landmark_series=[]
        )
        RepAssessment.objects.create(
            session=other_session, rep_number=1, landmark_series=[]
        )
