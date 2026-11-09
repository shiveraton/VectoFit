import hashlib
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError

from apps.datasets.models import Dataset, DatasetVideo
from apps.datasets.storage import dataset_video_storage


def digest(storage, name):
    checksum = hashlib.sha256()
    with storage.open(name, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.digest()


class Command(BaseCommand):
    help = "Copy referenced local dataset videos to R2 without changing object keys."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--source-root", default=str(settings.MEDIA_ROOT))

    def handle(self, *args, **options):
        if not settings.DATASET_R2_ENABLED:
            raise CommandError("Enable DATASET_R2_ENABLED to select the destination bucket.")
        source = FileSystemStorage(location=options["source_root"])
        target = dataset_video_storage()
        names = set()
        for model in (Dataset, DatasetVideo):
            names.update(model.objects.exclude(video_file="").exclude(video_file__isnull=True).values_list("video_file", flat=True).iterator())
        failures = 0
        for name in sorted(names):
            try:
                path = Path(source.path(name)).resolve()
                if not path.is_relative_to(Path(source.location).resolve()):
                    raise ValueError("Source path is outside the media root.")
                if not source.exists(name):
                    raise ValueError("Local source is missing; remote content cannot be verified.")
                expected = digest(source, name)
                if target.exists(name):
                    if digest(target, name) != expected:
                        raise ValueError("Remote object conflicts with the local source.")
                    self.stdout.write(f"VERIFIED {name}")
                    continue
                if options["dry_run"]:
                    self.stdout.write(f"WOULD COPY {name}")
                    continue
                with source.open(name, "rb") as file:
                    target.connection.meta.client.put_object(
                        Bucket=target.bucket_name, Key=name, Body=file,
                        IfNoneMatch="*",
                    )
                if digest(target, name) != expected:
                    raise ValueError("Uploaded content failed verification; local source retained.")
                self.stdout.write(f"COPIED {name}")
            except (OSError, ValueError, SuspiciousFileOperation, BotoCoreError, ClientError) as exc:
                failures += 1
                self.stderr.write(f"FAILED {name}: {type(exc).__name__}: {exc}")
        if failures:
            raise CommandError(f"{failures} video(s) could not be migrated. Fix reported files and rerun.")
        self.stdout.write(self.style.SUCCESS(f"Checked {len(names)} dataset video(s). Local originals retained."))
