from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from rest_framework.test import APITestCase

from apps.annotator.tests import AssignmentAccessTests
from .admin import DatasetAnnotatorAssignmentAdmin
from .models import DatasetAnnotatorAssignment, DatasetAssignmentEvent, KneeAnnotation


class AssignmentManagementTests(APITestCase):
    def setUp(self):
        AssignmentAccessTests.setUp(self)
        self.admin = get_user_model().objects.create_user(username="assignment-admin", is_staff=True)
        self.client.force_authenticate(self.admin)
        self.list_url = f"/api/datasets/{self.dataset.pk}/assignments/"
        self.detail_url = self.list_url + f"{self.other.pk}/"

    def set_access(self, active):
        return self.client.put(self.detail_url, {"is_active": active}, format="json")

    def test_grants_and_revocations_are_idempotent_and_audited(self):
        self.assertEqual(self.set_access(True).status_code, 200)
        self.assertEqual(self.set_access(True).status_code, 200)
        row = DatasetAnnotatorAssignment.objects.get(dataset=self.dataset, annotator=self.other)
        self.assertEqual(row.events.count(), 1)
        self.assertEqual(row.events.get().actor, self.admin)
        self.assertEqual(self.set_access(False).status_code, 200)
        self.assertEqual(self.set_access(False).status_code, 200)
        self.assertEqual(row.events.count(), 2)
        self.assertEqual(self.set_access(True).status_code, 200)
        self.assertEqual(DatasetAnnotatorAssignment.objects.get(dataset=self.dataset, annotator=self.other).pk, row.pk)
        self.assertEqual(row.events.count(), 3)
        events = self.client.get(self.list_url + "events/").data["results"]
        self.assertEqual([e["action"] for e in events], ["granted", "revoked", "granted"])

    def test_revoke_missing_assignment_is_noop(self):
        self.assertEqual(self.set_access(False).status_code, 200)
        self.assertFalse(DatasetAnnotatorAssignment.objects.filter(annotator=self.other).exists())
        self.assertFalse(DatasetAssignmentEvent.objects.exists())

    def test_shared_access_includes_all_annotators_and_can_be_disabled(self):
        response = self.client.put(
            self.list_url + "access-mode/", {"all_annotators_access": True}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.dataset.refresh_from_db()
        self.assertTrue(self.dataset.all_annotators_access)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/datasets/{self.dataset.pk}/annotation/").status_code, 200)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.put(
            self.list_url + "access-mode/", {"all_annotators_access": False}, format="json",
        ).status_code, 200)
        self.dataset.refresh_from_db()
        self.assertFalse(self.dataset.all_annotators_access)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/datasets/{self.dataset.pk}/annotation/").status_code, 404)

    def test_shared_access_does_not_grant_non_annotator_media_access(self):
        self.dataset.all_annotators_access = True
        self.dataset.save(update_fields=["all_annotators_access"])
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url).data
        self.assertTrue(response["all_annotators_access"])
        self.assertEqual(self.client.put(
            self.list_url + "access-mode/", {}, format="json",
        ).status_code, 400)

    def test_all_management_endpoints_are_staff_only(self):
        for user in (self.user, None):
            self.client.force_authenticate(user=user)
            for url in (self.list_url, self.list_url + "events/", "/api/datasets/annotators/"):
                self.assertIn(self.client.get(url).status_code, (401, 403))
            self.assertIn(self.set_access(True).status_code, (401, 403))
        self.assertFalse(DatasetAssignmentEvent.objects.exists())

    def test_invalid_grants_rejected_but_revocation_still_allowed(self):
        self.set_access(True)
        self.other.is_active = False
        self.other.save()
        self.assertEqual(self.set_access(True).status_code, 400)
        self.assertEqual(self.set_access(False).status_code, 200)
        self.other.is_active = True
        self.other.is_staff = True
        self.other.save()
        self.assertEqual(self.set_access(True).status_code, 400)
        self.other.is_staff = False
        self.other.save()
        self.other.profile.is_annotator = False
        self.other.profile.save()
        self.assertEqual(self.set_access(True).status_code, 400)

    def test_latest_per_person_rating_counts_and_clear_reduces_progress(self):
        annotation = {"left": {"grade": "aligned"}, "right": {"grade": "aligned"}}
        KneeAnnotation.objects.create(sample=self.sample, annotator=self.user, annotation=annotation)
        KneeAnnotation.objects.create(sample=self.sample, annotator=self.user, annotation=annotation)
        KneeAnnotation.objects.create(sample=self.sample, annotator=self.other, annotation=annotation)
        row = self.client.get(self.list_url).data["results"][0]
        self.assertEqual((row["reviewed_count"], row["sample_count"]), (1, 1))
        KneeAnnotation.objects.create(sample=self.sample, annotator=self.user, annotation=None)
        self.assertEqual(self.client.get(self.list_url).data["results"][0]["reviewed_count"], 0)
        self.video.requires_manual_review = False
        self.video.save()
        self.assertEqual(self.client.get(self.list_url).data["eligible_sample_count"], 0)

    def test_picker_is_searchable_paginated_and_filters_accounts(self):
        User = get_user_model()
        from apps.accounts.models import Profile
        for i in range(22):
            user = User.objects.create_user(username=f"picker-{i:02}")
            Profile.objects.create(user=user, is_annotator=True)
        page = self.client.get("/api/datasets/annotators/?search=picker-").data
        self.assertEqual(page["count"], 22)
        self.assertEqual(len(page["results"]), 20)
        self.assertIsNotNone(page["next"])
        second = self.client.get("/api/datasets/annotators/?search=picker-&page=2").data
        self.assertEqual(len(second["results"]), 2)
        self.assertEqual(self.client.get("/api/datasets/annotators/?search=assignment-admin").data["count"], 0)

    def test_missing_dataset_user_and_invalid_payload(self):
        self.assertEqual(self.client.get("/api/datasets/999999/assignments/").status_code, 404)
        self.assertEqual(self.client.put(self.list_url + "999999/", {"is_active": True}, format="json").status_code, 404)
        self.assertEqual(self.client.put(self.detail_url, {}, format="json").status_code, 400)

    def test_django_admin_uses_the_same_audited_transition(self):
        model_admin = DatasetAnnotatorAssignmentAdmin(DatasetAnnotatorAssignment, AdminSite())
        obj = DatasetAnnotatorAssignment(dataset=self.dataset, annotator=self.other, is_active=True)
        request = Mock(user=self.admin)
        model_admin.save_model(request, obj, None, False)
        self.assertIsNotNone(obj.pk)
        obj.is_active = False
        model_admin.save_model(request, obj, None, True)
        self.assertEqual(obj.events.count(), 2)
        self.assertFalse(model_admin.has_delete_permission(request, obj))

    @patch("apps.datasets.views.cv2.VideoCapture")
    def test_private_annotation_routes_honor_grant_and_revocation(self, capture):
        capture.return_value.get.return_value = 30
        self.client.force_authenticate(self.user)
        session_url = f"/api/datasets/{self.dataset.pk}/annotation/"
        rating_url = f"/api/datasets/dataset-samples/{self.sample.pk}/"
        self.assertEqual(self.client.get(session_url).status_code, 200)
        self.assertEqual(len(self.client.get("/api/datasets/annotation-datasets/").data), 1)
        self.assignment.is_active = False
        self.assignment.save()
        self.assertEqual(self.client.get(session_url).status_code, 404)
        self.assertEqual(self.client.get("/api/datasets/annotation-datasets/").data, [])
        self.assertEqual(self.client.patch(rating_url, {"knee_annotation": None}, format="json").status_code, 404)
