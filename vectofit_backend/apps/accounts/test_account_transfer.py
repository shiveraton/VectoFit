from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase

from apps.accounts.management.commands.transfer_annotator_accounts import transfer_accounts
from apps.accounts.models import Profile


class AccountTransferTests(TestCase):
    databases = {"default", "source"}

    def setUp(self):
        self.user = get_user_model().objects.db_manager("source").create_user(
            username="remote-rater", email="rater@example.test", password="test-password",
        )
        Profile.objects.using("source").create(user_id=self.user.pk, is_annotator=True)

    def test_preview_does_not_write(self):
        report = transfer_accounts("source", "default")
        self.assertEqual(report["accounts"][0]["username"], "remote-rater")
        self.assertEqual(report["created"], 0)
        self.assertFalse(get_user_model().objects.exists())

    def test_transfer_preserves_password_and_role_without_copying_source_id(self):
        get_user_model().objects.create_user(username="existing-local")
        with transaction.atomic():
            report = transfer_accounts("source", "default", apply=True)
        copied = get_user_model().objects.get(username=self.user.username)
        self.assertEqual(report["created"], 1)
        self.assertNotEqual(copied.pk, self.user.pk)
        self.assertEqual(copied.password, self.user.password)
        self.assertTrue(copied.check_password("test-password"))
        self.assertTrue(copied.profile.is_annotator)
        self.assertFalse(copied.is_staff)
        self.assertFalse(copied.is_superuser)
        self.assertEqual(get_user_model().objects.using("source").count(), 1)

    def test_conflict_blocks_every_account(self):
        get_user_model().objects.create_user(username="other", email="RATER@example.test")
        report = transfer_accounts("source", "default", apply=True)
        self.assertTrue(report["conflicts"])
        self.assertEqual(report["created"], 0)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_staff_and_inactive_accounts_are_excluded(self):
        self.user.is_staff = True
        self.user.save(using="source")
        self.assertEqual(transfer_accounts("source", "default")["accounts"], [])
        self.user.is_staff = False
        self.user.is_active = False
        self.user.save(using="source")
        self.assertEqual(transfer_accounts("source", "default")["accounts"], [])
