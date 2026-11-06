from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction

import logging
import os

from ..models import Dataset, DatasetSample, DatasetVideo
from apps.assessments.models import AssessmentSession, RepAssessment
from apps.assessments.services.video_processor import VideoProcessor
from apps.analytics.services.segmentation import segment_reps
from apps.exercises.models import ExerciseVariant
from .video_processing import process_video_repetitions

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task
def process_dataset_video_task(dataset_id, user_id):
    dataset = Dataset.objects.filter(pk=dataset_id).first()
    if dataset is None:
        logger.warning(
            "Skipping dataset video processing: dataset %s no longer exists.",
            dataset_id,
        )
        return "missing"

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
            replace_existing=True,
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

        exercise_variant_map = {
            "bodyweight_squat": ExerciseVariant.VariantType.BODYWEIGHT,
            "goblet_squat": ExerciseVariant.VariantType.GOBLET,
        }

        variant_type = exercise_variant_map.get(video.dataset.exercise_type)

        if variant_type is None:
            raise RuntimeError(
                f"Unsupported exercise type: {video.dataset.exercise_type}"
            )

        exercise_variant = (
            ExerciseVariant.objects.filter(
                variant_type=variant_type,
                is_active=True,
            )
            .order_by("id")
            .first()
        )

        if exercise_variant is None:
            raise RuntimeError(
                f"No active exercise variant for {video.dataset.exercise_type}."
            )

        result = VideoProcessor.process_video(video.video_file.path)

        if result.get("status") != "success":
            raise RuntimeError(
                result.get(
                    "message",
                    "Video processing failed.",
                )
            )

        valid_entries = [
            entry for entry in result.get("landmark_data", []) if entry.get("landmarks")
        ]

        if len(valid_entries) < 3:
            raise RuntimeError("Not enough valid pose frames were produced.")

        landmark_series = [entry["landmarks"] for entry in valid_entries]

        segmented_reps = segment_reps(landmark_series)

        if not segmented_reps:
            raise RuntimeError("No complete squat repetitions were detected.")

        with transaction.atomic():
            session = AssessmentSession.objects.create(
                user=user,
                exercise_variant=exercise_variant,
                video_file=video.video_file.name,
            )

            for rep_number, rep in enumerate(
                segmented_reps,
                start=1,
            ):
                start_index = rep["start"]
                end_index = rep["end"]

                rep_landmarks = valid_entries[start_index : end_index + 1]

                rep_assessment = RepAssessment.objects.create(
                    session=session,
                    rep_number=rep_number,
                    landmark_series=rep_landmarks,
                    start_frame=valid_entries[start_index]["frame_index"],
                    end_frame=valid_entries[end_index]["frame_index"],
                )

                DatasetSample.objects.create(
                    dataset=video.dataset,
                    dataset_video=video,
                    rep_assessment=rep_assessment,
                    is_correct=(
                        None if video.requires_manual_review else video.source_label
                    ),
                )

        video.status = DatasetVideo.Status.READY
        video.error_message = ""

        logger.info(
            "Dataset video %s processed: %s repetitions",
            video.pk,
            len(segmented_reps),
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
