from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import ActivityLog, Profile


class AdministrationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", "admin@example.com", "test-pass", is_staff=True)
        self.user = User.objects.create_user("member", "member@example.com", "test-pass")

    def test_directory_and_logs_require_staff_access(self):
        for endpoint in ["admin-users-list", "activity-logs-list"]:
            self.assertEqual(self.client.get(reverse(endpoint)).status_code, 401)
            self.client.force_authenticate(self.user)
            self.assertEqual(self.client.get(reverse(endpoint)).status_code, 403)
            self.client.force_authenticate(None)
        Profile.objects.create(user=self.admin, is_validator=True)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(reverse("admin-users-list")).status_code, 403)

    def test_directory_is_read_only_searchable_and_excludes_credentials(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("admin-users-list"), {"search": "MEMBER@"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["username"], "member")
        self.assertNotIn("password", row)
        self.assertNotIn("token", row)
        self.assertEqual(self.client.patch(reverse("admin-users-detail", args=[self.user.pk]), {"is_staff": True}).status_code, 405)

    def test_directory_paginates(self):
        User.objects.bulk_create([User(username=f"extra-{index}") for index in range(26)])
        self.client.force_authenticate(self.admin)
        first = self.client.get(reverse("admin-users-list"))
        self.assertEqual(len(first.data["results"]), 25)
        self.assertIsNotNone(first.data["next"])
        second = self.client.get(reverse("admin-users-list"), {"page": 2})
        self.assertEqual(len(second.data["results"]), 3)

    def test_sign_in_records_success_without_credentials(self):
        response = self.client.post(reverse("login"), {"identifier": "member", "password": "test-pass"})
        self.assertEqual(response.status_code, 200)
        entry = ActivityLog.objects.get()
        self.assertEqual(entry.action, "sign_in")
        self.assertEqual(entry.actor, self.user)
        self.assertEqual(entry.details, "")
        self.client.post(reverse("login"), {"identifier": "member", "password": "incorrect"})
        self.assertEqual(ActivityLog.objects.count(), 1)

    def test_registration_records_the_new_account(self):
        response = self.client.post(reverse("register"), {"username": "new-user", "email": "new@example.com", "password": "test-pass", "confirm_password": "test-pass"})
        self.assertEqual(response.status_code, 201)
        entry = ActivityLog.objects.get()
        self.assertEqual(entry.action, "registered")
        self.assertEqual(entry.actor_username, "new-user")

    def test_settings_update_only_the_authenticated_account_and_log_changes(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(reverse("me-detail", args=[self.user.pk]), {"username": "renamed", "email": "changed@example.com", "is_staff": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.admin.username, "renamed")
        self.assertTrue(self.admin.is_staff)
        self.assertEqual(self.user.username, "member")
        entry = ActivityLog.objects.get()
        self.assertEqual(entry.actor_username, "renamed")
        self.assertEqual(entry.details, "Updated email, username")
        self.assertNotIn("changed@example.com", entry.details)
        self.client.patch(reverse("me-detail", args=[self.admin.pk]), {"username": "renamed"})
        self.assertEqual(ActivityLog.objects.count(), 1)

    def test_invalid_settings_do_not_change_account_or_create_events(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(reverse("me-detail", args=[self.admin.pk]), {"username": "member", "email": "invalid"})
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.username, "admin")
        self.assertFalse(ActivityLog.objects.exists())

    def test_logs_filter_and_preserve_actor_name_after_rename(self):
        ActivityLog.objects.create(actor=self.user, actor_username="member", action="sign_in")
        ActivityLog.objects.create(actor=self.admin, actor_username="admin", action="registered")
        self.user.username = "renamed-member"
        self.user.save()
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("activity-logs-list"), {"action": "sign_in", "search": "member"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["actor_username"], "member")
        self.assertEqual(self.client.delete(reverse("activity-logs-detail", args=[response.data["results"][0]["id"]])).status_code, 405)

    def test_profile_updates_keep_existing_behavior(self):
        Profile.objects.create(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.patch(reverse("profile-current"), {"bio": "Updated biography"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ActivityLog.objects.exists())
