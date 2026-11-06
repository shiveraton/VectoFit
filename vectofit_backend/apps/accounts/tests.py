from django.contrib.auth import get_user_model
from contextlib import redirect_stdout
from io import StringIO
from django.http import HttpResponse
from django.http.request import validate_host
from corsheaders.middleware import CorsMiddleware
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Profile


class DeploymentOriginTests(SimpleTestCase):
    @override_settings(
        ALLOWED_HOSTS=["api.vectofit.test"],
        CORS_ALLOWED_ORIGINS=["https://admin.vectofit.test"],
    )
    def test_untrusted_hosts_are_rejected_and_configured_origins_are_allowed(self):
        from django.conf import settings

        self.assertTrue(validate_host("api.vectofit.test", settings.ALLOWED_HOSTS))
        self.assertFalse(validate_host("attacker.example", settings.ALLOWED_HOSTS))

        request = RequestFactory().get(
            "/",
            HTTP_ORIGIN="https://admin.vectofit.test",
        )
        response = CorsMiddleware(lambda _request: HttpResponse("ok"))(request)
        self.assertEqual(
            response["Access-Control-Allow-Origin"], "https://admin.vectofit.test"
        )


class RegistrationTests(APITestCase):
    def test_login_does_not_print_credentials_or_request_body(self):
        output = StringIO()
        with redirect_stdout(output):
            response = self.client.post(
                reverse("login"),
                {"identifier": "missing-user", "password": "secret-test-password"},
                format="json",
            )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("secret-test-password", output.getvalue())
        self.assertNotIn("missing-user", output.getvalue())

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
