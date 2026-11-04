from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Profile


class RegistrationTests(APITestCase):
    def test_current_user_without_profile_is_not_an_annotator(self):
        user = get_user_model().objects.create_user(
            username="existing-user",
            password="test-pass",
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("me-list"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_annotator"])

    def test_registration_can_create_an_annotator(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-annotator",
                "email": "new@example.com",
                "password": "test-pass",
                "confirm_password": "test-pass",
                "is_annotator": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Profile.objects.get(user__username="new-annotator").is_annotator
        )
