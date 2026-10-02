from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ExerciseVariant

User = get_user_model()

class ExerciseVariantModelTests(APITestCase):
    def test_str_returns_name(self):
        variant = ExerciseVariant.objects.create(
            name="Bodyweight Squat",
            variant_type=ExerciseVariant.VariantType.BODYWEIGHT,
        )
        self.assertEqual(str(variant), "Bodyweight Squat")


class ExerciseVariantAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jhed", password="pass12345")
        self.active_variant = ExerciseVariant.objects.create(
            name="Bodyweight Squat",
            variant_type=ExerciseVariant.VariantType.BODYWEIGHT,
            is_active=True,
        )
        self.inactive_variant = ExerciseVariant.objects.create(
            name="Barbell Squat",
            variant_type=ExerciseVariant.VariantType.BARBELL,
            is_active=False,
        )
        self.client.force_authenticate(self.user)

    def test_list_includes_inactive_variants(self):
        response = self.client.get(reverse("exercisevariant-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_response_includes_is_active_flag(self):
        response = self.client.get(reverse("exercisevariant-list"))

        names_by_active = {item["name"]: item["is_active"] for item in response.data}
        self.assertTrue(names_by_active["Bodyweight Squat"])
        self.assertFalse(names_by_active["Barbell Squat"])

    def test_retrieve_returns_id_for_session_creation(self):
        url = reverse("exercisevariant-detail", args=[self.active_variant.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.active_variant.pk)

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("exercisevariant-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_not_allowed(self):
        url = reverse("exercisevariant-list")
        response = self.client.post(
            url, {"name": "Sneaky Variant", "variant_type": "BW"}
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        url = reverse("exercisevariant-detail", args=[self.active_variant.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)