import io
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage, Storage
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIRequestFactory

from apps.analytics.utils.file_resolver import resolved_video_path
from apps.datasets.models import Dataset, DatasetVideo
from apps.datasets.services.import_executor import (
    _delete_stored_files,
    _store_archive_videos,
)
from apps.datasets.services.media import protected_file_response


class RemoteStorage(Storage):
    def __init__(self):
        self.files = InMemoryStorage()

    def _open(self, name, mode="rb"):
        return self.files.open(name, mode)

    def _save(self, name, content):
        return self.files.save(name, content)

    def exists(self, name):
        return self.files.exists(name)

    def size(self, name):
        return self.files.size(name)

    def delete(self, name):
        self.files.delete(name)


class DatasetStorageTests(SimpleTestCase):
    def setUp(self):
        self.storage = RemoteStorage()
        self.name = self.storage.save("videos/test.mp4", ContentFile(b"0123456789"))
        self.file = SimpleNamespace(storage=self.storage, name=self.name)

    def test_remote_video_materialized_and_removed_on_failure(self):
        with self.assertRaisesRegex(RuntimeError, "processing failed"), resolved_video_path(self.file) as path:
            self.assertEqual(Path(path).read_bytes(), b"0123456789")
            raise RuntimeError("processing failed")
        self.assertFalse(Path(path).exists())

    def test_dataset_wrapper_remains_supported(self):
        with resolved_video_path(SimpleNamespace(video_file=self.file)) as path:
            self.assertTrue(Path(path).is_file())
        self.assertFalse(Path(path).exists())

    def test_fields_use_dataset_storage_and_remote_ranges_work(self):
        for model in (Dataset, DatasetVideo):
            field = model._meta.get_field("video_file")
            with patch.object(field, "storage", self.storage):
                instance = model(video_file=self.name)
                request = APIRequestFactory().get("/", HTTP_RANGE="bytes=2-5")
                response = protected_file_response(request, instance.video_file)
                self.assertEqual(response.status_code, 206)
                self.assertEqual(b"".join(response.streaming_content), b"2345")
                response.close()

    def test_single_video_upload_uses_field_storage(self):
        field = Dataset._meta.get_field("video_file")
        with patch.object(field, "storage", self.storage):
            dataset = Dataset()
            dataset.video_file.save("upload.mp4", ContentFile(b"upload"), save=False)
            self.assertEqual(self.storage.open(dataset.video_file.name).read(), b"upload")

    def test_processing_remote_video_cleans_up_on_processor_failure(self):
        from apps.datasets.services.video_processing import process_video_repetitions

        paths = []

        def process(path):
            paths.append(path)
            self.assertEqual(Path(path).read_bytes(), b"0123456789")
            return {"status": "error", "message": "processor failed"}

        with patch("apps.datasets.services.video_processing.ExerciseVariant.objects.filter") as variants, patch(
            "apps.datasets.services.video_processing.VideoProcessor.process_video", side_effect=process,
        ):
            variants.return_value.order_by.return_value.first.return_value = object()
            with self.assertRaisesRegex(RuntimeError, "processor failed"):
                process_video_repetitions(
                    dataset=SimpleNamespace(exercise_type="bodyweight_squat"),
                    video_file=self.file, user=None,
                )
        self.assertEqual(len(paths), 1)
        self.assertFalse(Path(paths[0]).exists())

    def test_zip_import_and_cleanup_use_dataset_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "videos.zip"
            with zipfile.ZipFile(archive, "w") as file:
                file.writestr("test.mp4", b"video")
            with patch("apps.datasets.services.import_executor.dataset_video_storage", return_value=self.storage):
                names, mapping, size = _store_archive_videos(archive, [{"archive_path": "test.mp4"}])
                self.assertEqual(size, 5)
                self.assertEqual(self.storage.open(mapping["test.mp4"]).read(), b"video")
                _delete_stored_files(names)
                self.assertFalse(self.storage.exists(names[0]))


class DatasetMigrationTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.name = "datasets/videos/old.mp4"
        path = Path(self.directory.name) / self.name
        path.parent.mkdir(parents=True)
        path.write_bytes(b"original")
        Dataset.objects.create(name="Migration", exercise_type="bodyweight_squat", purpose="training", video_file=self.name)
        self.storage = RemoteStorage()

    def migrate(self, **options):
        from django.core.management import call_command
        with override_settings(DATASET_R2_ENABLED=True), patch(
            "apps.datasets.management.commands.migrate_dataset_videos.dataset_video_storage",
            return_value=self.storage,
        ):
            call_command("migrate_dataset_videos", source_root=self.directory.name, stdout=io.StringIO(), stderr=io.StringIO(), **options)

    def test_dry_run_does_not_upload(self):
        self.migrate(dry_run=True)
        self.assertFalse(self.storage.exists(self.name))

    def test_identical_objects_are_verified(self):
        self.storage.save(self.name, ContentFile(b"original"))
        self.migrate()
        self.assertEqual(self.storage.open(self.name).read(), b"original")

    def test_conflicts_are_not_overwritten(self):
        from django.core.management.base import CommandError
        self.storage.save(self.name, ContentFile(b"different"))
        with self.assertRaises(CommandError):
            self.migrate()
        self.assertEqual(self.storage.open(self.name).read(), b"different")

    def test_missing_local_files_are_reported(self):
        from django.core.management.base import CommandError
        (Path(self.directory.name) / self.name).unlink()
        with self.assertRaises(CommandError):
            self.migrate(dry_run=True)

    def test_copy_preserves_key_and_local_original(self):
        def put_object(**kwargs):
            self.assertEqual(kwargs["Key"], self.name)
            self.assertEqual(kwargs["IfNoneMatch"], "*")
            self.storage.save(kwargs["Key"], ContentFile(kwargs["Body"].read()))

        self.storage.bucket_name = "test-bucket"
        self.storage.connection = Mock()
        self.storage.connection.meta.client.put_object.side_effect = put_object
        self.migrate()
        self.assertEqual(self.storage.open(self.name).read(), b"original")
        self.assertEqual((Path(self.directory.name) / self.name).read_bytes(), b"original")
