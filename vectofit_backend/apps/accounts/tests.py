from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from .roles import ANNOTATOR_GROUP


class AnnotatorAccountTests(TestCase):
    def test_create_annotator_is_non_staff_and_idempotent(self):
        with patch(
            "apps.accounts.management.commands.create_annotator.getpass",
            return_value="secure-password",
        ):
            call_command(
                "create_annotator",
                username="annotator-one",
                email="annotator@example.com",
                stdout=StringIO(),
            )
            call_command(
                "create_annotator",
                username="annotator-one",
                email="annotator@example.com",
                stdout=StringIO(),
            )
        user = get_user_model().objects.get(username="annotator-one")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password("secure-password"))
        self.assertTrue(user.groups.filter(name=ANNOTATOR_GROUP).exists())

    def test_existing_user_is_only_added_with_promote_flag(self):
        user = get_user_model().objects.create_user("existing", password="password")
        call_command(
            "create_annotator",
            username="existing",
            email="existing@example.com",
            stdout=StringIO(),
        )
        self.assertFalse(user.groups.exists())
        call_command(
            "create_annotator",
            username="existing",
            email="existing@example.com",
            promote_existing=True,
            stdout=StringIO(),
        )
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertTrue(user.groups.filter(name=ANNOTATOR_GROUP).exists())

    def test_current_user_exposes_read_only_role_fields(self):
        user = get_user_model().objects.create_user("annotator", password="password")
        Group.objects.get_or_create(name=ANNOTATOR_GROUP)[0].user_set.add(user)
        client = APIClient()
        client.force_authenticate(user)
        response = client.get("/api/accounts/me/")
        self.assertEqual(response.data["role"], "annotator")
        self.assertFalse(response.data["is_staff"])
        self.assertTrue(response.data["is_annotator"])
        response = client.patch(
            f"/api/accounts/me/{user.pk}/",
            {"is_staff": True, "is_annotator": False, "role": "admin"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertEqual(response.data["role"], "annotator")
