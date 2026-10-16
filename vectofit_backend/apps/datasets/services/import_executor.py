import json
import logging
import uuid
import zipfile

from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import NotFound, ValidationError

from ..models import Dataset, DatasetVideo, Participant, ViewAngle


logger = logging.getLogger(__name__)

STAGING_DIR = Path(settings.MEDIA_ROOT) / "dataset_import_staging"

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".avi",
}

ALLOWED_ANGLES = {
    "diagonal",
    "frontal",
    "sagittal",
}

MAX_PARTICIPANT_CODE_LENGTH = 32
MAX_SOURCE_PATH_LENGTH = 255


def _get_stage_paths(token):
    token = uuid.UUID(str(token))
    token_key = token.hex

    archive_path = STAGING_DIR / f"{token_key}.zip"
    metadata_path = STAGING_DIR / f"{token_key}.json"

    return archive_path, metadata_path


def _load_staged_import(token, user):
    archive_path, metadata_path = _get_stage_paths(token)

    if not metadata_path.is_file() or not archive_path.is_file():
        raise NotFound(
            "Import preview was not found or has expired. "
            "Please upload the ZIP again."
        )

    try:
        with metadata_path.open("r", encoding="utf-8") as file:
            stage = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read import staging metadata: %s", exc)
        raise NotFound("The import preview is invalid.") from exc

    if str(stage.get("user_id")) != str(user.pk):
        raise NotFound("Import preview was not found.")

    try:
        expired = (
            float(stage["expires_at"]) <= timezone.now().timestamp()
        )
    except (KeyError, TypeError, ValueError):
        raise ValidationError({
            "token": "The import preview has invalid expiration metadata."
        })

    if expired:
        archive_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)

        raise ValidationError({
            "token": "The import preview has expired. Please upload again."
        })

    manifest = stage.get("manifest")

    if not isinstance(manifest, dict):
        raise ValidationError({
            "token": "The import preview has an invalid manifest."
        })

    if manifest.get("errors"):
        raise ValidationError({
            "token": (
                "The archive preview contains errors. "
                "Correct the archive and preview it again."
            )
        })

    videos = stage.get("videos")

    if not isinstance(videos, list) or not videos:
        raise ValidationError({
            "token": "The archive contains no valid videos to import."
        })

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]

            if len(names) != len(set(names)):
                raise ValidationError({
                    "token": "The ZIP contains duplicate file paths."
                })

            entry_by_name = {
                entry.filename: entry for entry in entries
            }

            seen_paths = set()

            for video in videos:
                if not isinstance(video, dict):
                    raise ValidationError({
                        "token": "The video manifest contains an invalid entry."
                    })

                member_name = video.get("archive_path")

                if not isinstance(member_name, str) or not member_name:
                    raise ValidationError({
                        "token": "A video is missing its archive path."
                    })

                member_path = PurePosixPath(member_name)

                if (
                    member_path.is_absolute()
                    or ".." in member_path.parts
                    or "\\" in member_name
                    or member_name in seen_paths
                ):
                    raise ValidationError({
                        "token": f"Invalid or duplicate video path: {member_name}"
                    })

                seen_paths.add(member_name)

                entry = entry_by_name.get(member_name)

                if entry is None or entry.is_dir():
                    raise ValidationError({
                        "token": f"Video not found in ZIP: {member_name}"
                    })

                if entry.file_size <= 0:
                    raise ValidationError({
                        "token": f"Video is empty: {member_name}"
                    })

                suffix = member_path.suffix.lower()

                if suffix not in ALLOWED_VIDEO_EXTENSIONS:
                    raise ValidationError({
                        "token": f"Unsupported video format: {member_name}"
                    })

                participant_code = video.get("participant_code")

                if (
                    not isinstance(participant_code, str)
                    or not participant_code.strip()
                    or len(participant_code.strip())
                    > MAX_PARTICIPANT_CODE_LENGTH
                ):
                    raise ValidationError({
                        "token": f"Invalid participant code: {member_name}"
                    })

                if video.get("angle_variant") not in ALLOWED_ANGLES:
                    raise ValidationError({
                        "token": f"Invalid camera angle: {member_name}"
                    })

                source_label = video.get("source_label")

                if source_label is not None and not isinstance(
                    source_label, bool
                ):
                    raise ValidationError({
                        "token": f"Invalid source label: {member_name}"
                    })

                if len(member_name) > MAX_SOURCE_PATH_LENGTH:
                    raise ValidationError({
                        "token": f"Archive path is too long: {member_name}"
                    })

    except zipfile.BadZipFile as exc:
        raise ValidationError({
            "token": "The staged archive is not a valid ZIP file."
        }) from exc

    return archive_path, metadata_path, videos


def execute_bulk_import(*, validated_data, user):
    archive_path, metadata_path, videos = _load_staged_import(
        validated_data["token"],
        user,
    )

    stored_file_names = []
    video_ids = []

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            with transaction.atomic():
                dataset = Dataset.objects.create(
                    name=validated_data["name"],
                    description=validated_data.get("description", ""),
                    exercise_type=validated_data["exercise_type"],
                    purpose=validated_data["purpose"],
                    primary_target=validated_data.get(
                        "primary_target",
                        "biomechanical_errors",
                    ),
                    secondary_target=validated_data.get(
                        "secondary_target",
                        "biomechanical_errors",
                    ),
                    status="PENDING",
                )

                for item in videos:
                    member_name = item["archive_path"]
                    suffix = PurePosixPath(member_name).suffix.lower()

                    participant, _ = Participant.objects.get_or_create(
                        participant_code=item["participant_code"].strip()
                    )

                    view_angle, _ = ViewAngle.objects.get_or_create(
                        angle_variant=item["angle_variant"]
                    )
                    storage_name = (
                        f"datasets/videos/{uuid.uuid4().hex}{suffix}"
                    )

                    with archive.open(member_name, "r") as member:
                        content = File(
                            member,
                            name=Path(storage_name).name,
                        )

                        stored_name = default_storage.save(
                            storage_name,
                            content,
                        )

                    stored_file_names.append(stored_name)

                    video = DatasetVideo.objects.create(
                        dataset=dataset,
                        participant=participant,
                        view_angle=view_angle,
                        video_file=stored_name,
                        source_label=item["source_label"],
                        source_path=member_name,
                        status=DatasetVideo.Status.PENDING,
                    )

                    video_ids.append(video.pk)

    except Exception:
        for stored_name in stored_file_names:
            try:
                default_storage.delete(stored_name)
            except Exception:
                logger.exception(
                    "Could not clean up imported file: %s",
                    stored_name,
                )

        raise

    archive_path.unlink(missing_ok=True)
    metadata_path.unlink(missing_ok=True)

    from .tasks import (
        process_dataset_video_item_task,
        refresh_dataset_collection_status,
    )

    queue_failures = []

    for video_id in video_ids:
        try:
            process_dataset_video_item_task.delay(
                video_id,
                user.pk,
            )

        except Exception as exc:
            logger.exception(
                "Could not queue processing for DatasetVideo %s",
                video_id,
            )

            DatasetVideo.objects.filter(pk=video_id).update(
                status=DatasetVideo.Status.FAILED,
                error_message=f"Could not queue processing task: {exc}",
            )

            queue_failures.append({
                "video_id": video_id,
                "error": str(exc),
            })

    refresh_dataset_collection_status(dataset.pk)
    
    dataset.refresh_from_db()

    return {
        "dataset": dataset,
        "imported_videos": len(video_ids),
        "queued_videos": len(video_ids) - len(queue_failures),
        "queue_failures": queue_failures,
    }