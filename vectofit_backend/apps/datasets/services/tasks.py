import logging

from celery import shared_task
from django.contrib.auth import get_user_model

from ..models import Dataset, DatasetVideo
from .video_processing import process_video_repetitions

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task
def process_dataset_video_task(dataset_id, user_id):
    dataset = Dataset.objects.get(pk=dataset_id)
    dataset.status = "PROCESSING"
    dataset.error_message = ""
    dataset.save(update_fields=["status", "error_message"])

    try:
        if dataset.participant_id is None:
            raise RuntimeError("A participant must be assigned.")

        user = User.objects.get(pk=user_id)

        process_video_repetitions(
            dataset=dataset,
            video_file=dataset.video_file,
            user=user,
        )

        dataset.status = "READY"

    except Exception as exc:
        logger.exception("Dataset %s processing failed.", dataset_id)
        dataset.status = "FAILED"
        dataset.error_message = str(exc)

    finally:
        dataset.save(update_fields=["status", "error_message"])


def refresh_dataset_collection_status(dataset_id):
    statuses = list(
        DatasetVideo.objects.filter(dataset_id=dataset_id).values_list(
            "status", flat=True
        )
    )

    if not statuses:
        return

    pending = {
        DatasetVideo.Status.PENDING,
        DatasetVideo.Status.PROCESSING,
    }

    if any(item in pending for item in statuses):
        aggregate_status = "PROCESSING"
    elif all(item == DatasetVideo.Status.READY for item in statuses):
        aggregate_status = "READY"
    elif all(item == DatasetVideo.Status.FAILED for item in statuses):
        aggregate_status = "FAILED"
    else:
        aggregate_status = "PARTIAL"

    failed_count = statuses.count(DatasetVideo.Status.FAILED)

    dataset = Dataset.objects.get(pk=dataset_id)
    dataset.status = aggregate_status
    dataset.error_message = (
        f"{failed_count} video(s) failed processing." if failed_count else ""
    )
    dataset.save(update_fields=["status", "error_message"])


@shared_task
def process_dataset_video_item_task(dataset_video_id, user_id):
    video = DatasetVideo.objects.select_related(
        "dataset",
        "participant",
        "view_angle",
    ).get(pk=dataset_video_id)

    if video.status == DatasetVideo.Status.READY:
        return

    video.status = DatasetVideo.Status.PROCESSING
    video.error_message = ""
    video.save(update_fields=["status", "error_message", "updated_at"])

    logger.info(
        "Processing dataset video %s: %s",
        video.pk,
        video.video_file.name if video.video_file else None,
    )

    try:
        if not video.video_file:
            raise RuntimeError("No video file is attached.")

        user = User.objects.get(pk=user_id)

        process_video_repetitions(
            dataset=video.dataset,
            video_file=video.video_file,
            user=user,
            dataset_video=video,
            replace_existing=False,
        )

        video.status = DatasetVideo.Status.READY
        video.error_message = ""

        logger.info(
            "Dataset video %s processed: %s repetitions",
            video.pk,
            video.samples.count(),
        )

    except Exception as exc:
        logger.exception(
            "Dataset video %s processing failed",
            video.pk,
        )

        video.status = DatasetVideo.Status.FAILED
        video.error_message = str(exc)

    finally:
        video.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )

        refresh_dataset_collection_status(video.dataset_id)
