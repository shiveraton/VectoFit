from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from assessments.models import AssessmentSession, RepAssessment
from exercises.models import ExerciseVariant

User = get_user_model()

def _create_session_with_reps(user, variant, hybrid_scores, created_at=None):
    session = AssessmentSession.objects.create(user=user, exercise_variant=variant)
    if created_at is not None:
        AssessmentSession.objects.filter(pk=session.pk).update(created_at=created_at)
        session.refresh_from_db()
    for i, score in enumerate(hybrid_scores, start=1):
        RepAssessment.objects.create(
            session=session, rep_number=i, hybrid_scores=score, landmark_series=[]
        )
        return session

class WeeklyTrendViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jhed", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass 12345")
        self.variant = ExerciseVariant.objects.create(
            name="Bodyweight Squat", variant_type=ExerciseVariant.VariantType.BODYWEIGHT
        )
        self.client.force_authenticate(self.user)

    def test_this_week_aggregates_only_this_weeks_reps(self):
        today = timezone.localdate()
        week_start = today - timezone.timedelta(days=today.weekday())

        _create_session_with_reps(
            self.user, self.variant, [80.0, 90.0], created_at=timezone.now()
        )

        _create_session_with_reps(
            self.user,
            self.variant,
            [10.0],
            created_at=timezone.now() - timezone.timedelta(days=14),
        )

        response = self.client.get(reverse("weekly-trend"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["session_count"], 1)
        self.assertEqual(response.data["rep_count"], 2)
        self.assertEqual(response.data["avg_hybrid_score"], 85.0)
        self.assertEqual(response.data["week_start"], week_start.isoformat())

    def test_other_users_reps_excluded(self):
        _create_session_with_reps(self.other_user, self.variant, [50.0])

        response = self.client.get(reverse("weekly-trend"))

        self.assertEqual(response.data["session_count"], 0)
        self.assertEqual(response.data["rep_count"], 0)
        self.assertEqual(response.data["avg_hybrid_score"])

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("weekly-trend"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class TrendSeriesViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(name="jhed", password="pass12345")
        self.variant = ExerciseVariant.objects.create(
            name="Goblet Squat", variant_type=ExerciseVariant.VariantType.GOBLET
        )
        self.client.force_authenticate(self.user)

    def test_buckets_by_week_by_default(self):
        _create_session_with_reps(self.user, self.variant, [70.0], created_at=timezone.now())

        response = self.client.get(reverse("trend-series"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["rep_count"], 1)

    def test_month_period_param(self):
        _create_session_with_reps(self.user, self.variant, [70.0], created_at=timezone.now())

        response = self.client.get(reverse("trend-series"), {"period": "month"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

class VariantTrendViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(name="jhed", password="pass12345")
        self.bw_variant = ExerciseVariant.objects.create(
            name="Bodyweight Squat", variant_type=ExerciseVariant.VariantType.BODYWEIGHT
        )
        self.goblet_variant = ExerciseVariant.objects.create(
            name="Goblet Squat", variant_type=ExerciseVariant.VariantType.GOBLET
        )
        self.client.force_authenticate(self.user)

    def test_filters_to_requested_variant_only(self):
        _create_session_with_reps(self.user, self.bw_variant, [80.0], created_at=timezone.now())

        response = self.client.get(reverse("variant-trend", args=[self.bw_variant.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["exercise_variant_name"], "Bodyweight Squat")

        self.assertEqual(len(response.data["points"], 1))
        self.assertEqual(response.data["period"][0]["rep_count"], 1)