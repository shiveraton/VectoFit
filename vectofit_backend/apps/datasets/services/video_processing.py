from apps.analytics.services.features import compute_rep_fppa
from apps.analytics.services.fppa import FEATURE_SCHEMA_VERSION as FPPA_SCHEMA_VERSION
from apps.analytics.services.fppa import extract_fppa_features
from apps.analytics.services.landmark_schema import (
    legacy_frame,
    serialize_landmark_frames,
)
from apps.analytics.services.repetitions import extract_reps
from apps.assessments.models import AssessmentSession, RepAssessment
from apps.assessments.services.video_processor import VideoProcessor
from apps.exercises.models import ExerciseVariant
from django.db import transaction

from ..models import DatasetSample

EXERCISE_VARIANTS = {
    "bodyweight_squat": ExerciseVariant.VariantType.BODYWEIGHT,
    "goblet_squat": ExerciseVariant.VariantType.GOBLET,
}


def process_video_repetitions(
    *, dataset, video_file, user, dataset_video=None, replace_existing=False
):
    if not video_file:
        raise RuntimeError("No video file is attached.")
    variant_type = EXERCISE_VARIANTS.get(dataset.exercise_type)
    if variant_type is None:
        raise RuntimeError(f"Unsupported exercise type: {dataset.exercise_type}")
    exercise_variant = (
        ExerciseVariant.objects.filter(variant_type=variant_type, is_active=True)
        .order_by("id")
        .first()
    )
    if exercise_variant is None:
        raise RuntimeError(f"No active exercise variant for {dataset.exercise_type}.")

    extraction = extract_reps(video_file.path)
    if not extraction["reps"]:
        raise RuntimeError("No complete squat repetitions were detected.")
    result = extraction["result"]
    with transaction.atomic():
        if replace_existing:
            AssessmentSession.objects.filter(dataset=dataset).delete()
        session = AssessmentSession.objects.create(
            dataset=dataset,
            user=user,
            exercise_variant=exercise_variant,
            video_file=video_file.name,
            processed_frame_width=result["processed_frame_width"],
            processed_frame_height=result["processed_frame_height"],
            rotation_metadata_degrees=result["rotation_metadata_degrees"],
            rotation_auto_enabled=result["rotation_auto_enabled"],
            pipeline_config_hash=extraction["pipeline_config_hash"],
            landmark_schema_version=result["landmark_schema_version"],
            missing_runs=result["missing_runs"],
        )
        dataset.pipeline_config_hash = extraction["pipeline_config_hash"]
        dataset.save(update_fields=["pipeline_config_hash"])
        for number, rep in enumerate(extraction["reps"], start=1):
            entries = rep["entries"]
            fppa_frames = serialize_landmark_frames(entries)["frames"]
            features, validity = extract_fppa_features(
                fppa_frames,
                frame_width=result["processed_frame_width"],
                frame_height=result["processed_frame_height"],
                native_fps=result["native_fps"],
                sample_step=extraction["sample_step"],
            )
            assessment = RepAssessment.objects.create(
                session=session,
                rep_number=number,
                landmark_series=[legacy_frame(entry) for entry in entries],
                landmark_data=serialize_landmark_frames(entries),
                missing_runs=[],
                landmark_schema_version="landmarks_v2",
                pipeline_config_hash=extraction["pipeline_config_hash"],
                feature_schema_version=FPPA_SCHEMA_VERSION,
                analysis_result={
                    "fppa_v2": {
                        "schema_version": FPPA_SCHEMA_VERSION,
                        "validity": validity,
                        **({"features": features} if features is not None else {}),
                    }
                },
                start_frame=rep["start"],
                end_frame=rep["end"],
                key_frame_index=rep["key_frame_index"],
            )
            sample_data = {"dataset": dataset, "rep_assessment": assessment}
            if dataset_video is not None:
                sample_data["dataset_video"] = dataset_video
            DatasetSample.objects.create(**sample_data)
        invalid_reps = sum(
            not item["analysis_result"]["fppa_v2"]["validity"]["valid"]
            for item in RepAssessment.objects.filter(session=session).only(
                "analysis_result"
            )
        )
        session.report = {
            "fppa_v2_summary": {
                "total_reps": len(extraction["reps"]),
                "invalid_reps": invalid_reps,
                "valid_reps": len(extraction["reps"]) - invalid_reps,
            }
        }
        session.status = AssessmentSession.Status.COMPLETED
        session.save(update_fields=["status", "report"])
    return len(extraction["reps"])


def backfill_rep_landmark_data(
    *,
    dataset,
    user,
    angle_variant=None,
    dry_run=False,
) -> dict:
    """Backfill landmark_data for labelled reps that were created before the pipeline
    stored landmarks.

    Only updates existing rows in place. Never creates new DatasetSample /
    RepAssessment / AssessmentSession rows, never deletes anything, and never
    touches is_correct / error_label / annotator / label_source.

    Safe to run on videos whose status is already READY.

    Returns a summary dict with per-video details and aggregate counts.
    """
    import logging

    logger = logging.getLogger(__name__)

    samples = (
        DatasetSample.objects.filter(
            dataset=dataset,
            is_correct__isnull=False,
            rep_assessment__landmark_data__isnull=True,
        )
        .select_related(
            "rep_assessment",
            "rep_assessment__session",
            "dataset_video",
            "dataset_video__view_angle",
        )
        .order_by("dataset_video_id", "rep_assessment__rep_number")
    )

    if angle_variant:
        samples = samples.filter(
            dataset_video__view_angle__angle_variant=angle_variant
        )

    samples = list(samples)
    if not samples:
        return {
            "dataset_id": dataset.pk,
            "angle_variant": angle_variant,
            "dry_run": dry_run,
            "videos": [],
            "total_samples": 0,
            "updated_reps": 0,
            "skipped_mismatch": 0,
            "skipped_no_video": 0,
            "skipped_no_session": 0,
        }

    videos = {}
    for sample in samples:
        video = sample.dataset_video
        if video is None:
            continue
        videos.setdefault(video.pk, {"video": video, "samples": []})["samples"].append(
            sample
        )

    results = []
    total_updated = 0
    total_skipped_mismatch = 0
    total_skipped_no_video = 0
    total_skipped_no_session = 0

    for video_pk, group in sorted(videos.items()):
        video = group["video"]
        group_samples = group["samples"]

        video_result = {
            "video_id": video.pk,
            "view_angle": (
                video.view_angle.angle_variant if video.view_angle else None
            ),
            "samples": len(group_samples),
            "updated": 0,
            "skipped_mismatch": 0,
            "skipped_no_session": 0,
            "error": None,
        }

        if video.video_file is None:
            video_result["error"] = "No video file attached."
            results.append(video_result)
            total_skipped_no_video += len(group_samples)
            continue

        session_ids = {
            s.rep_assessment.session_id
            for s in group_samples
            if s.rep_assessment and s.rep_assessment.session_id
        }
        sessions = {
            s.pk: s
            for s in AssessmentSession.objects.filter(pk__in=session_ids)
        }

        rep_assessments = {}
        for s in group_samples:
            rep = s.rep_assessment
            if rep is None or rep.session_id not in sessions:
                video_result["skipped_no_session"] += 1
                total_skipped_no_session += 1
                continue
            rep_assessments[(rep.session_id, rep.rep_number)] = rep

        if not rep_assessments:
            results.append(video_result)
            continue

        if dry_run:
            try:
                result = VideoProcessor.process_video(video.video_file.path)
            except Exception as exc:
                video_result["error"] = f"Video processing failed: {exc}"
                results.append(video_result)
                continue

            landmark_entries = result.get("landmark_data", [])
            frame_indices = {
                int(entry.get("frame_index", -1))
                for entry in landmark_entries
                if entry.get("frame_index") is not None
            }
            matched = 0
            mismatch = 0
            for (session_id, rep_number), rep in rep_assessments.items():
                if rep.start_frame is None or rep.end_frame is None:
                    mismatch += 1
                    continue
                has_frames = any(
                    rep.start_frame <= fi <= rep.end_frame for fi in frame_indices
                )
                if has_frames:
                    matched += 1
                else:
                    mismatch += 1
            video_result["updated"] = matched
            video_result["skipped_mismatch"] = mismatch
            total_updated += matched
            total_skipped_mismatch += mismatch
            results.append(video_result)
            continue

        try:
            result = VideoProcessor.process_video(video.video_file.path)
        except Exception as exc:
            logger.exception("Backfill video processing failed for video %s", video.pk)
            video_result["error"] = f"Video processing failed: {exc}"
            results.append(video_result)
            continue

        landmark_entries = result.get("landmark_data", [])
        entry_by_frame = {}
        for entry in landmark_entries:
            fi = entry.get("frame_index")
            if fi is not None:
                entry_by_frame[int(fi)] = entry

        processed_width = result.get("processed_frame_width")
        processed_height = result.get("processed_frame_height")

        updates = []
        matched = 0
        mismatch = 0
        for (session_id, rep_number), rep in rep_assessments.items():
            if rep.start_frame is None or rep.end_frame is None:
                mismatch += 1
                continue

            window_entries = []
            for fi in range(rep.start_frame, rep.end_frame + 1):
                entry = entry_by_frame.get(fi)
                if entry is not None:
                    window_entries.append(entry)

            if not window_entries:
                mismatch += 1
                continue

            window_entries.sort(key=lambda e: int(e.get("frame_index", 0)))

            entries = window_entries
            landmark_data = serialize_landmark_frames(entries)
            fppa, fppa_status = compute_rep_fppa(
                landmark_data,
                frame_width=processed_width,
                frame_height=processed_height,
            )

            analysis_result = {
                "fppa_v2": {
                    "schema_version": FPPA_SCHEMA_VERSION,
                    "validity": fppa_status,
                    **({"features": fppa} if fppa is not None else {}),
                }
            }

            rep.landmark_data = landmark_data
            rep.landmark_series = [legacy_frame(entry) for entry in entries]
            rep.analysis_result = analysis_result
            rep.landmark_schema_version = "landmarks_v2"
            rep.pipeline_config_hash = result.get("pipeline_config_hash", "")
            rep.feature_schema_version = FPPA_SCHEMA_VERSION
            rep.missing_runs = result.get("missing_runs", [])

            if rep.start_frame is None:
                rep.start_frame = int(entries[0].get("frame_index", 0))
            if rep.end_frame is None:
                rep.end_frame = int(entries[-1].get("frame_index", 0))
            if rep.key_frame_index is None:
                mid = len(entries) // 2
                rep.key_frame_index = int(entries[mid].get("frame_index", 0))

            updates.append(rep)
            matched += 1

        with transaction.atomic():
            sessions_to_update = {rep.session_id for rep in updates}
            for session_id in sessions_to_update:
                session = sessions[session_id]
                session.processed_frame_width = processed_width
                session.processed_frame_height = processed_height
                session.rotation_metadata_degrees = result.get(
                    "rotation_metadata_degrees"
                )
                session.rotation_auto_enabled = result.get("rotation_auto_enabled")
                session.pipeline_config_hash = result.get(
                    "pipeline_config_hash", ""
                )
                session.landmark_schema_version = "landmarks_v2"
                session.missing_runs = result.get("missing_runs", [])
                session.save(
                    update_fields=[
                        "processed_frame_width",
                        "processed_frame_height",
                        "rotation_metadata_degrees",
                        "rotation_auto_enabled",
                        "pipeline_config_hash",
                        "landmark_schema_version",
                        "missing_runs",
                    ]
                )

            for rep in updates:
                rep.save(
                    update_fields=[
                        "landmark_data",
                        "landmark_series",
                        "analysis_result",
                        "start_frame",
                        "end_frame",
                        "key_frame_index",
                        "landmark_schema_version",
                        "pipeline_config_hash",
                        "feature_schema_version",
                        "missing_runs",
                    ]
                )

        video_result["updated"] = matched
        video_result["skipped_mismatch"] = mismatch
        total_updated += matched
        total_skipped_mismatch += mismatch
        results.append(video_result)

    return {
        "dataset_id": dataset.pk,
        "angle_variant": angle_variant,
        "dry_run": dry_run,
        "videos": results,
        "total_samples": len(samples),
        "updated_reps": total_updated,
        "skipped_mismatch": total_skipped_mismatch,
        "skipped_no_video": total_skipped_no_video,
        "skipped_no_session": total_skipped_no_session,
    }
