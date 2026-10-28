from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.exercises.models import ExerciseVariant
from .models import AssessmentSession, BodyProfile, RepAssessment

User = get_user_model()

class BodyProfileModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jhed", password="pass12345")

    def test_str_includes_username(self):
        profile = BodyProfile.objects.create(
            user = self.user,
            height_cm = 170,
            torso_length_cm = 55,
            femur_length_cm = 45,
            tibia_length_cm = 40,
            scale_factor = 1.02
        )
        self.assertIn(self.user.username, str(profile))

class AssessmentSessionAPITests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="jhed", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")
        self.variant = ExerciseVariant.objects.create(
            exercise_variant="Bodyweight Squat",
            name="Bodyweight Squat",
            variant_type=ExerciseVariant.VariantType.BODYWEIGHT
        )
        self.client.force_authenticate(self.user)

    def test_session_list_scoped_to_requesting_user(self):
        AssessmentSession.objects.create(user=self.user, exercise_variant=self.variant)
        AssessmentSession.objects.create(user=self.other_user, exercise_variant=self.variant)

        response = self.client.get(reverse("assessment-session-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("assessment-session-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_uses_detail_serializer_with_reps(self):
        session = AssessmentSession.objects.create(user=self.user, exercise_variant=self.variant)
        RepAssessment.objects.create(session=session, rep_number=1, landmark_series=[])

        response = self.client.get(reverse("assessment-session-detail", args=[session.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["reps"]), 1)

class RepAssessmentModelTests(APITestCase):
    @classmethod
    def setUp(self):
        self.user = User.objects.create_user(username="jhed", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")
        self.variant = ExerciseVariant.objects.create(
            exercise_variant="Goblet Squat",
            name="Goblet Squat",
            variant_type=ExerciseVariant.VariantType.GOBLET
        )
        self.session = AssessmentSession.objects.create(
            user = self.user, exercise_variant=self.variant
        )

    def test_rep_number_unique_per_session(self):
        RepAssessment.objects.create(session=self.session, rep_number=1, landmark_series=[])
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
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
        RepAssessment.objects.create(session=other_session, rep_number=1, landmark_series=[])