from unittest.mock import patch

from rest_framework.test import APITestCase

from apps.annotator import tests as annotator_tests
from apps.datasets.models import DatasetVideo


class ImportedDatasetRetryTests(APITestCase):
    setUp = annotator_tests.AssignmentAccessTests.setUp

    def prepare(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.dataset.status = "FAILED"
        self.dataset.save(update_fields=["status"])
        self.video.status = "FAILED"
        self.video.save(update_fields=["status"])
        return DatasetVideo.objects.create(
            dataset=self.dataset,
            participant=self.video.participant,
            view_angle=self.video.view_angle,
            video_file="ready.mp4",
            status="READY",
        )

    @patch("apps.datasets.views.process_dataset_video_task.delay")
    @patch("apps.datasets.views.process_dataset_video_item_task.delay")
    def test_retry_queues_failed_collection_video_and_preserves_ready(
        self, item_task, legacy_task
    ):
        ready = self.prepare()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f"/api/datasets/{self.dataset.pk}/retry/")
        self.assertEqual(response.status_code, 202)
        item_task.assert_called_once_with(self.video.pk, self.user.pk)
        legacy_task.assert_not_called()
        ready.refresh_from_db()
        self.video.refresh_from_db()
        self.assertEqual(ready.status, "READY")
        self.assertEqual(self.video.status, "PENDING")

    @patch(
        "apps.datasets.views.process_dataset_video_item_task.delay",
        side_effect=RuntimeError("broker unavailable"),
    )
    def test_failed_queue_keeps_video_retryable(self, item_task):
        self.prepare()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f"/api/datasets/{self.dataset.pk}/retry/")
        self.assertEqual(response.status_code, 202)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, "FAILED")
        self.assertIn("broker unavailable", self.video.error_message)


    @patch("apps.datasets.views.process_dataset_video_item_task.delay")
    def test_partial_collection_can_retry_only_failed_videos(self, item_task):
        self.prepare()
        self.dataset.status = "PARTIAL"
        self.dataset.save(update_fields=["status"])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f"/api/datasets/{self.dataset.pk}/retry/")
        self.assertEqual(response.status_code, 202)
        item_task.assert_called_once_with(self.video.pk, self.user.pk)
