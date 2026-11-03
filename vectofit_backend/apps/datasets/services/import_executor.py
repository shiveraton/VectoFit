import json
import logging
import time
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
COPY_CHUNK_SIZE = 4 * 1024 * 1024
DB_INSERT_BATCH_SIZE = 100

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi"}
ALLOWED_ANGLES = {"diagonal", "frontal", "sagittal"}
MAX_PARTICIPANT_CODE_LENGTH = 32
MAX_SOURCE_PATH_LENGTH = 255


class ChunkedStorageFile(File):
    """Stream ZIP members to storage using larger I/O chunks."""

    def chunks(self, chunk_size=COPY_CHUNK_SIZE):
        while True:
            chunk = self.read(chunk_size)
            if not chunk:
                break
            yield chunk


def _get_stage_paths(token):
    token_key = uuid.UUID(str(token)).hex
    return (
        STAGING_DIR / f"{token_key}.zip",
        STAGING_DIR / f"{token_key}.json",
    )


def _load_staged_import(token, user):
    archive_path, metadata_path = _get_stage_paths(token)

    if not metadata_path.is_file() or not archive_path.is_file():
        raise NotFound(
            "Import preview was not found or has expired. Please upload the ZIP again."
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
        expired = float(stage["expires_at"]) <= timezone.now().timestamp()
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(
            {"upload_token": ("The import preview has invalid expiration metadata.")}
        ) from exc

    if expired:
        archive_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise ValidationError(
            {"upload_token": ("The import preview has expired. Please upload again.")}
        )

    manifest = stage.get("manifest")
    if not isinstance(manifest, dict):
        raise ValidationError(
            {"upload_token": "The import preview has an invalid manifest."}
        )

    if manifest.get("errors"):
        raise ValidationError(
            {
                "upload_token": (
                    "The archive preview contains errors. "
                    "Correct the archive and preview it again."
                )
            }
        )

    videos = stage.get("videos")
    if not isinstance(videos, list) or not videos:
        raise ValidationError(
            {"upload_token": "The archive contains no valid videos to import."}
        )

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            entries = archive.infolist()
            entry_by_name = {entry.filename: entry for entry in entries}

            if len(entry_by_name) != len(entries):
                raise ValidationError(
                    {"upload_token": "The ZIP contains duplicate file paths."}
                )

            seen_paths = set()

            for video in videos:
                if not isinstance(video, dict):
                    raise ValidationError(
                        {
                            "upload_token": (
                                "The video manifest contains an invalid entry."
                            )
                        }
                    )

                member_name = video.get("archive_path")
                if not isinstance(member_name, str) or not member_name:
                    raise ValidationError(
                        {"upload_token": ("A video is missing its archive path.")}
                    )

                member_path = PurePosixPath(member_name)

                if (
                    member_path.is_absolute()
                    or ".." in member_path.parts
                    or "\\" in member_name
                    or member_name in seen_paths
                ):
                    raise ValidationError(
                        {
                            "upload_token": (
                                f"Invalid or duplicate video path: {member_name}"
                            )
                        }
                    )

                seen_paths.add(member_name)
                entry = entry_by_name.get(member_name)

                if entry is None or entry.is_dir():
                    raise ValidationError(
                        {"upload_token": (f"Video not found in ZIP: {member_name}")}
                    )

                if entry.file_size <= 0:
                    raise ValidationError(
                        {"upload_token": f"Video is empty: {member_name}"}
                    )

                if member_path.suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
                    raise ValidationError(
                        {"upload_token": (f"Unsupported video format: {member_name}")}
                    )

                participant_code = video.get("participant_code")
                if (
                    not isinstance(participant_code, str)
                    or not participant_code.strip()
                    or len(participant_code.strip()) > MAX_PARTICIPANT_CODE_LENGTH
                ):
                    raise ValidationError(
                        {"upload_token": (f"Invalid participant code: {member_name}")}
                    )

                if video.get("angle_variant") not in ALLOWED_ANGLES:
                    raise ValidationError(
                        {"upload_token": (f"Invalid camera angle: {member_name}")}
                    )

                source_label = video.get("source_label")
                if source_label is not None and not isinstance(source_label, bool):
                    raise ValidationError(
                        {"upload_token": (f"Invalid source label: {member_name}")}
                    )

                if len(member_name) > MAX_SOURCE_PATH_LENGTH:
                    raise ValidationError(
                        {"upload_token": (f"Archive path is too long: {member_name}")}
                    )

    except zipfile.BadZipFile as exc:
        raise ValidationError(
            {"upload_token": "The staged archive is not a valid ZIP file."}
        ) from exc

    return archive_path, metadata_path, videos


def _delete_stored_files(stored_file_names):
    for stored_name in stored_file_names:
        try:
            default_storage.delete(stored_name)
        except Exception:
            logger.exception(
                "Could not clean up imported file: %s",
                stored_name,
            )


def _store_archive_videos(archive_path, videos):
    """
    Copy videos to permanent storage before opening the database transaction.
    """
    stored_file_names = []
    stored_by_archive_path = {}
    bytes_copied = 0

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            entries = {entry.filename: entry for entry in archive.infolist()}

            for item in videos:
                member_name = item["archive_path"]
                suffix = PurePosixPath(member_name).suffix.lower()
                storage_name = f"datasets/videos/{uuid.uuid4().hex}{suffix}"

                with archive.open(member_name, "r") as member:
                    content = ChunkedStorageFile(
                        member,
                        name=Path(storage_name).name,
                    )
                    stored_name = default_storage.save(
                        storage_name,
                        content,
                    )

                stored_file_names.append(stored_name)
                stored_by_archive_path[member_name] = stored_name
                bytes_copied += entries[member_name].file_size

    except Exception:
        _delete_stored_files(stored_file_names)
        raise

    return stored_file_names, stored_by_archive_path, bytes_copied


def _create_dataset_records(
    *,
    validated_data,
    videos,
    stored_by_archive_path,
):
    """Keep the database transaction focused on database operations."""
    with transaction.atomic():
        dataset = Dataset.objects.create(
            name=validated_data["name"],
            description=validated_data.get("description", ""),
            exercise_type=validated_data["exercise_type"],
            purpose=validated_data["purpose"],
            primary_target=validated_data.get("primary_target", "biomechanical_errors"),
            secondary_target=validated_data.get(
                "secondary_target", "biomechanical_errors"
            ),
            review_policy=validated_data.get(
                "review_policy", Dataset.ReviewPolicy.SOURCE
            ),
            selection_method=validated_data.get(
                "selection_method", Dataset.SelectionMethod.STRATIFIED
            ),
            review_count=validated_data.get("review_count"),
            random_seed=validated_data.get("random_seed"),
            selected_video_paths=validated_data.get("selected_video_paths", []),
            status="PENDING",
        )

        selected_paths = set(validated_data.get("selected_video_paths", []))

        participant_codes = {item["participant_code"].strip() for item in videos}

        participants_by_code = {
            participant.participant_code: participant
            for participant in Participant.objects.filter(
                participant_code__in=participant_codes
            )
        }

        angle_values = {item["angle_variant"] for item in videos}

        angles_by_value = {
            angle.angle_variant: angle
            for angle in ViewAngle.objects.filter(angle_variant__in=angle_values)
        }

        video_objects = []

        for item in videos:
            participant_code = item["participant_code"].strip()
            participant = participants_by_code.get(participant_code)

            if participant is None:
                participant, _ = Participant.objects.get_or_create(
                    participant_code=participant_code
                )
                participants_by_code[participant_code] = participant

            angle_value = item["angle_variant"]
            view_angle = angles_by_value.get(angle_value)

            if view_angle is None:
                view_angle, _ = ViewAngle.objects.get_or_create(
                    angle_variant=angle_value
                )
                angles_by_value[angle_value] = view_angle

            member_name = item["archive_path"]
            requires_manual_review = (
                dataset.review_policy == Dataset.ReviewPolicy.ALL
                or (
                    dataset.review_policy == Dataset.ReviewPolicy.SUBSET
                    and member_name in selected_paths
                )
            )

            video_objects.append(
                DatasetVideo(
                    dataset=dataset,
                    participant=participant,
                    view_angle=view_angle,
                    video_file=stored_by_archive_path[member_name],
                    source_label=item["source_label"],
                    source_path=member_name,
                    requires_manual_review=requires_manual_review,
                    status=DatasetVideo.Status.PENDING,
                )
            )

        DatasetVideo.objects.bulk_create(
            video_objects,
            batch_size=DB_INSERT_BATCH_SIZE,
        )

        video_ids = list(
            DatasetVideo.objects.filter(dataset=dataset)
            .order_by("id")
            .values_list("id", flat=True)
        )

    return dataset, video_ids


def _remove_stage_files(archive_path, metadata_path):
    for path in (archive_path, metadata_path):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning(
                "Could not remove import staging file %s",
                path,
                exc_info=True,
            )


def execute_bulk_import(*, validated_data, user):
    started_at = time.perf_counter()

    archive_path, metadata_path, videos = _load_staged_import(
        validated_data["upload_token"],
        user,
    )

    selected_paths = validated_data.get("selected_video_paths", [])
    available_paths = {item["archive_path"] for item in videos}
    unknown_paths = set(selected_paths) - available_paths
    if unknown_paths:
        raise ValidationError(
            {
                "selected_video_paths": (
                    "Selected paths are not present in the staged archive: "
                    + ", ".join(sorted(unknown_paths))
                )
            }
        )

    copy_started_at = time.perf_counter()
    stored_file_names = []

    try:
        (
            stored_file_names,
            stored_by_archive_path,
            bytes_copied,
        ) = _store_archive_videos(archive_path, videos)

        copy_seconds = time.perf_counter() - copy_started_at
        db_started_at = time.perf_counter()

        dataset, video_ids = _create_dataset_records(
            validated_data=validated_data,
            videos=videos,
            stored_by_archive_path=stored_by_archive_path,
        )

        db_seconds = time.perf_counter() - db_started_at

    except Exception:
        _delete_stored_files(stored_file_names)
        raise

    # Permanent video files and database rows now exist.
    _remove_stage_files(archive_path, metadata_path)

    logger.info(
        "Dataset import prepared: dataset_id=%s videos=%s "
        "extracted_bytes=%s storage_copy_seconds=%.2f "
        "database_seconds=%.2f elapsed_seconds=%.2f",
        dataset.pk,
        len(video_ids),
        bytes_copied,
        copy_seconds,
        db_seconds,
        time.perf_counter() - started_at,
    )

    from .tasks import (
        process_dataset_video_item_task,
        refresh_dataset_collection_status,
    )

    queue_failures = []
    queue_started_at = time.perf_counter()

    for video_id in video_ids:
        try:
            process_dataset_video_item_task.delay(video_id, user.pk)
        except Exception as exc:
            logger.exception(
                "Could not queue processing for DatasetVideo %s",
                video_id,
            )

            DatasetVideo.objects.filter(pk=video_id).update(
                status=DatasetVideo.Status.FAILED,
                error_message=f"Could not queue processing task: {exc}",
            )

            queue_failures.append(
                {
                    "video_id": video_id,
                    "error": str(exc),
                }
            )

    try:
        refresh_dataset_collection_status(dataset.pk)
    except Exception:
        logger.exception(
            "Could not refresh status for imported dataset %s",
            dataset.pk,
        )

    dataset.refresh_from_db()

    logger.info(
        "Dataset import queued: dataset_id=%s videos=%s "
        "queue_failures=%s queue_seconds=%.2f total_seconds=%.2f",
        dataset.pk,
        len(video_ids),
        len(queue_failures),
        time.perf_counter() - queue_started_at,
        time.perf_counter() - started_at,
    )

    return {
        "dataset": dataset,
        "imported_videos": len(video_ids),
        "queued_videos": len(video_ids) - len(queue_failures),
        "queue_failures": queue_failures,
    }
