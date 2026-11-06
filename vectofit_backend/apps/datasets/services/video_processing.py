from django.db import transaction

from apps.assessments.models import AssessmentSession, RepAssessment
from apps.assessments.services.video_processor import VideoProcessor
from apps.analytics.services.segmentation import (
    segment_reps,
    split_contiguous_pose_runs,
)
from apps.exercises.models import ExerciseVariant

from ..models import DatasetSample


EXERCISE_VARIANTS = {
    "bodyweight_squat": ExerciseVariant.VariantType.BODYWEIGHT,
    "goblet_squat": ExerciseVariant.VariantType.GOBLET,
}


def process_video_repetitions(
    *,
    dataset,
    video_file,
    user,
    dataset_video=None,
    replace_existing=False,
):

    if not video_file:
        raise RuntimeError("No video file is attached.")

    variant_type = EXERCISE_VARIANTS.get(dataset.exercise_type)

    if variant_type is None:
        raise RuntimeError(
            f"Unsupported exercise type: {dataset.exercise_type}"
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
            f"No active exercise variant for {dataset.exercise_type}."
        )

    result = VideoProcessor.process_video(video_file.path)

    if result.get("status") != "success":
        raise RuntimeError(
            result.get("message", "Video processing failed.")
        )

    landmark_data = result.get("landmark_data", [])
    native_fps = float(result.get("native_fps") or 30.0)
    expected_frame_step = max(1, round(native_fps / 30.0))
    pose_runs = split_contiguous_pose_runs(
        landmark_data,
        expected_frame_step=expected_frame_step,
    )

    if sum(len(run) for run in pose_runs) < 3:
        raise RuntimeError("Not enough valid pose frames were produced.")

    segmented_repetitions = []
    for run in pose_runs:
        if len(run) < 3:
            continue

        repetitions = segment_reps([entry["landmarks"] for entry in run])
        segmented_repetitions.extend(
            (run, repetition) for repetition in repetitions
        )

    if not segmented_repetitions:
        raise RuntimeError("No complete squat repetitions were detected.")

    with transaction.atomic():
        if replace_existing:
            AssessmentSession.objects.filter(dataset=dataset).delete()

        session = AssessmentSession.objects.create(
            dataset=dataset,
            user=user,
            exercise_variant=exercise_variant,
            video_file=video_file.name,
        )

        for number, (run, rep) in enumerate(segmented_repetitions, start=1):
            start, end = rep["start"], rep["end"]

            if start < 0 or end < start or end >= len(run):
                raise RuntimeError(
                    f"Invalid frame range for repetition {number}."
                )

            rep_entries = run[start:end + 1]

            assessment = RepAssessment.objects.create(
                session=session,
                rep_number=number,
                landmark_series=rep_entries,
                start_frame=rep_entries[0]["frame_index"],
                end_frame=rep_entries[-1]["frame_index"],
            )

            sample_data = {
                "dataset": dataset,
                "rep_assessment": assessment,
            }

            if dataset_video is not None:
                sample_data.update(
                    dataset_video=dataset_video,
                    is_correct=dataset_video.source_label,
                )

            DatasetSample.objects.create(**sample_data)

        session.status = AssessmentSession.Status.COMPLETED
        session.save(update_fields=["status"])

    return len(segmented_repetitions)
