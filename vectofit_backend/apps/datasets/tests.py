import io
import tempfile
import uuid
import zipfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Dataset
from .serializers import DatasetBulkImportSerializer

User = get_user_model()


class DatasetAPITests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password123"
        )
        self.regular_user = User.objects.create_user(
            username="user", email="user@example.com", password="password123"
        )

        self.dataset = Dataset.objects.create(
            name="Bench Press Form",
            description="Tracking bar path and velocity",
            exercise_type="Strength",
            purpose="Validation",
            primary_target="Pectorals",
        )
        self.list_url = reverse("dataset-list")

    def test_unauthenticated_user_denied_access(self):
        response = self.client.get(self.list_url)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_regular_user_denied_access(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_list_datasets(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_admin_user_can_create_dataset(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Squat Depth Dataset",
            "description": "3D pose estimation keypoints",
            "exercise_type": "bodyweight_squat",
            "purpose": "training",
            "primary_target": "Quadriceps",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Dataset.objects.count(), 2)


class DatasetImportContractTests(APITestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.admin_user = User.objects.create_superuser(
            username="import-admin",
            email="import-admin@example.com",
            password="password123",
        )
        self.client.force_authenticate(user=self.admin_user)

        self.preview_url = reverse("dataset-import-preview")
        self.import_url = reverse("dataset_bulk_import")

    def make_archive_upload(self):
        archive_bytes = io.BytesIO()

        with zipfile.ZipFile(archive_bytes, "w") as archive:
            archive.writestr(
                "good/diagonal/P01.mp4",
                b"representative-video-content",
            )

        return SimpleUploadedFile(
            "dataset.zip",
            archive_bytes.getvalue(),
            content_type="application/zip",
        )

    def bulk_import_payload(self, upload_token=None):
        return {
            "upload_token": str(upload_token or uuid.uuid4()),
            "name": "Imported Squat Dataset",
            "description": "Contract-test dataset",
            "exercise_type": "bodyweight_squat",
            "purpose": "training",
            "primary_target": "squat_quality",
            "secondary_target": "biomechanical_errors",
        }

    def test_preview_response_has_nested_manifest_contract(self):
        response = self.client.post(
            self.preview_url,
            {"zip_file": self.make_archive_upload()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data["upload_token"], (str, type(None)))
        self.assertIsInstance(response.data["expires_at"], (int, float))
        self.assertIsInstance(response.data["manifest"], dict)

        manifest = response.data["manifest"]
        for field_name in (
            "file_count",
            "participant_count",
            "ignored_file_count",
        ):
            self.assertIsInstance(manifest[field_name], int)

        for label in ("good", "bad"):
            self.assertIsInstance(manifest["by_label"][label], int)

        for angle in ("diagonal", "frontal", "sagittal"):
            self.assertIsInstance(manifest["by_angle"][angle], int)

        for field_name in ("files", "warnings", "errors"):
            self.assertIsInstance(manifest[field_name], list)

    def test_bulk_import_serializer_accepts_upload_token(self):
        upload_token = uuid.uuid4()
        serializer = DatasetBulkImportSerializer(
            data=self.bulk_import_payload(upload_token)
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["upload_token"], upload_token)

    def test_bulk_import_serializer_requires_upload_token(self):
        payload = self.bulk_import_payload()
        payload.pop("upload_token")

        serializer = DatasetBulkImportSerializer(data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("upload_token", serializer.errors)

    def test_bulk_import_serializer_accepts_source_all_and_subset_policies(self):
        for policy, paths in (
            ("source", []),
            ("all", []),
            ("subset", ["good/diagonal/P01.mp4"]),
        ):
            payload = self.bulk_import_payload()
            payload.update(
                {
                    "review_policy": policy,
                    "selection_method": "manual",
                    "review_count": len(paths) if policy == "subset" else None,
                    "selected_video_paths": paths,
                }
            )
            serializer = DatasetBulkImportSerializer(data=payload)
            self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_bulk_import_serializer_rejects_invalid_subset_selection(self):
        payload = self.bulk_import_payload()
        payload.update(
            {
                "review_policy": "subset",
                "selection_method": "manual",
                "review_count": 2,
                "selected_video_paths": ["good/diagonal/P01.mp4"],
            }
        )
        serializer = DatasetBulkImportSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("review_count", serializer.errors)

        payload["review_count"] = 0
        payload["selected_video_paths"] = []
        serializer = DatasetBulkImportSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("selected_video_paths", serializer.errors)

    def test_bulk_import_serializer_rejects_unsupported_review_policy(self):
        payload = self.bulk_import_payload()
        payload.update(
            {
                "review_policy": "random",
                "selection_method": "manual",
                "selected_video_paths": [],
            }
        )

        serializer = DatasetBulkImportSerializer(data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("review_policy", serializer.errors)

    def test_bulk_import_serializer_rejects_unsupported_selection_method(self):
        payload = self.bulk_import_payload()
        payload.update(
            {
                "review_policy": "subset",
                "selection_method": "automatic",
                "review_count": 1,
                "selected_video_paths": ["good/diagonal/P01.mp4"],
            }
        )

        serializer = DatasetBulkImportSerializer(data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("selection_method", serializer.errors)

    def test_bulk_import_serializer_rejects_duplicate_selected_paths(self):
        payload = self.bulk_import_payload()
        payload.update(
            {
                "review_policy": "subset",
                "selection_method": "manual",
                "review_count": 2,
                "selected_video_paths": [
                    "good/diagonal/P01.mp4",
                    "good/diagonal/P01.mp4",
                ],
            }
        )

        serializer = DatasetBulkImportSerializer(data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("selected_video_paths", serializer.errors)

    @patch("apps.datasets.views.execute_bulk_import")
    def test_bulk_import_response_serializes_dataset_and_import_summary(
        self,
        execute_bulk_import,
    ):
        dataset = Dataset.objects.create(
            name="Imported Squat Dataset",
            description="Contract-test dataset",
            exercise_type="bodyweight_squat",
            purpose="training",
            primary_target="squat_quality",
            secondary_target="biomechanical_errors",
            status="PROCESSING",
        )
        queue_failures = [{"video_id": 12, "error": "Broker unavailable"}]
        execute_bulk_import.return_value = {
            "dataset": dataset,
            "imported_videos": 3,
            "queued_videos": 2,
            "queue_failures": queue_failures,
        }

        response = self.client.post(
            self.import_url,
            self.bulk_import_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["dataset"]["id"], dataset.pk)
        self.assertEqual(response.data["dataset"]["name"], dataset.name)
        self.assertEqual(response.data["dataset"]["status"], "PROCESSING")
        self.assertEqual(response.data["imported_videos"], 3)
        self.assertEqual(response.data["queued_videos"], 2)
        self.assertEqual(response.data["queue_failures"], queue_failures)
        execute_bulk_import.assert_called_once()
