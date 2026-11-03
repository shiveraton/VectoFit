from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .roles import ANNOTATOR_GROUP, annotator_group, is_annotator

REGISTER_URL = "/api/accounts/register/"


class AnnotatorRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def register(self, **overrides):
        payload = {
            "username": "new-annotator",
            "email": "annotator@example.com",
            "password": "annotator-pass-9812",
            "confirm_password": "annotator-pass-9812",
        }
        payload.update(overrides)
        return self.client.post(REGISTER_URL, payload, format="json")

    def test_registration_creates_annotator_and_returns_token(self):
        response = self.register()

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["token"])
        self.assertEqual(response.data["user"]["role"], "annotator")
        self.assertTrue(response.data["user"]["is_annotator"])

        user = get_user_model().objects.get(username="new-annotator")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password("annotator-pass-9812"))
        self.assertTrue(user.groups.filter(name=ANNOTATOR_GROUP).exists())
        self.assertTrue(is_annotator(user))

    def test_token_from_registration_authenticates_immediately(self):
        token = self.register().data["token"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        response = client.get("/api/accounts/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "annotator")

    def test_duplicate_username_and_email_are_rejected(self):
        get_user_model().objects.create_user(
            "taken-user", email="taken@example.com", password="annotator-pass-9812"
        )

        response = self.register(username="taken-user")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

        response = self.register(email="taken@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_password_mismatch_and_weak_password_are_rejected(self):
        response = self.register(confirm_password="something-else-9812")
        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm_password", response.data)

        response = self.register(password="123", confirm_password="123")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    @override_settings(ANNOTATOR_INVITE_CODE="let-me-in")
    def test_invite_code_is_required_when_configured(self):
        response = self.register()
        self.assertEqual(response.status_code, 400)
        self.assertIn("invite_code", response.data)

        response = self.register(invite_code="wrong")
        self.assertEqual(response.status_code, 400)

        response = self.register(invite_code="let-me-in")
        self.assertEqual(response.status_code, 201, response.data)

    @override_settings(ANNOTATOR_SELF_REGISTRATION=False)
    def test_registration_can_be_disabled(self):
        response = self.register()

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            get_user_model().objects.filter(username="new-annotator").exists()
        )


class AnnotatorDirectoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            "admin", "admin@example.com", "admin-pass-9812"
        )
        self.annotator = User.objects.create_user(
            "annotator", password="annotator-pass-9812"
        )
        self.annotator.groups.add(annotator_group())

    def test_admin_sees_annotators_only(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/accounts/annotators/")

        self.assertEqual(response.status_code, 200)
        usernames = [row["username"] for row in response.data]
        self.assertEqual(usernames, ["annotator"])
        self.assertEqual(response.data[0]["assigned_datasets"], 0)

    def test_annotator_cannot_list_the_directory(self):
        self.client.force_authenticate(self.annotator)

        response = self.client.get("/api/accounts/annotators/")

        self.assertEqual(response.status_code, 403)
