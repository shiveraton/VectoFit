from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Profile


@override_settings(ANNOTATOR_INVITATION_CODE="enrollment-test-invitation")
class PublicEnrollmentRoleTests(APITestCase):
    def test_public_registration_creates_discoverable_role_and_usable_login(self):
        browser = APIClient(enforce_csrf_checks=True)
        csrf = browser.get("/api/annotator/csrf/").data["csrfToken"]
        credentials = {"username": "enrollment-rater", "password": "Enrollment-Test-Pass-938!"}
        response = browser.post("/api/annotator/register/", {
            **credentials, "email": "enrollment@example.test",
            "confirm_password": credentials["password"],
            "invitation_code": "enrollment-test-invitation",
        }, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 201, response.data)
        user = get_user_model().objects.get(username=credentials["username"])
        self.assertTrue(Profile.objects.get(user=user).is_annotator)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(credentials["password"]))
        admin = get_user_model().objects.create_user(username="enrollment-admin", is_staff=True)
        staff = APIClient()
        staff.force_authenticate(admin)
        response = staff.get("/api/datasets/annotators/?search=enrollment-rater")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [user.pk])
        response = browser.post("/api/annotator/login/", credentials, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["is_annotator"])
        self.assertEqual(browser.get("/api/annotator/me/").data["id"], user.pk)
