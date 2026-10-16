from django.db import transaction

from apps.assessments.models import AssessmentSession, RepAssessment
from apps.assessments.services.video_processor import VideoProcessor
from apps.analytics.services.segmentation import segment_reps
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

    entries = [
        entry
        for entry in result.get("landmark_data", [])
        if entry.get("landmarks")
    ]

    if len(entries) < 3:
        raise RuntimeError("Not enough valid pose frames were produced.")

    repetitions = segment_reps(
        [entry["landmarks"] for entry in entries]
    )

    if not repetitions:
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

        for number, rep in enumerate(repetitions, start=1):
            start, end = rep["start"], rep["end"]

            if start < 0 or end < start or end >= len(entries):
                raise RuntimeError(
                    f"Invalid frame range for repetition {number}."
                )

            rep_entries = entries[start:end + 1]

            assessment = RepAssessment.objects.create(
                session=session,
                rep_number=number,
                landmark_series=[
                    entry["landmarks"] for entry in rep_entries
                ],
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

    return len(repetitions)