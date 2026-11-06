import logging
from typing import Any

import numpy as np
from django.db import transaction
from django.utils import timezone

from apps.analytics.services.fppa import (
    FEATURE_SCHEMA_VERSION as FPPA_SCHEMA_VERSION,
    evaluate_fppa,
    extract_fppa_features,
)
from apps.analytics.services.features import FeatureExtractionError
from apps.analytics.services.segmentation import (
    segment_reps,
    split_contiguous_pose_runs,
)
from apps.analytics.services.session_report import build_session_report
from apps.training.services.model_inference import (
    ModelInferenceError,
    predict_with_active_model,
)

from ..models import AssessmentSession, RepAssessment
from .snapshot_overlay import reference_template_from_profile
from .video_processor import VideoProcessor

logger = logging.getLogger(__name__)


def _scale_factor_for_session(session):
    if session is None or session.body_profile_id is None:
        return None

    return session.body_profile.scale_factor or None

def _split_contiguous_pose_runs(
    landmark_data: list[dict[str, Any]],
    expected_frame_step: int,
) -> list[list[dict[str, Any]]]:
    return split_contiguous_pose_runs(
        landmark_data,
        expected_frame_step,
    )

def _collect_repetition_entries(
    session_id: int,
    landmark_data: list[dict[str, Any]],
    expected_frame_step: int,
) -> list[dict[str, Any]]:
    pose_runs = _split_contiguous_pose_runs(
        landmark_data,
        expected_frame_step=expected_frame_step,
    )

    repetition_entries: list[dict[str, Any]] = []

    run_gaps = [
        (previous[-1]["frame_index"], current[0]["frame_index"])
        for previous, current in zip(pose_runs, pose_runs[1:])
    ]
    logger.info(
        "[RepCount] session=%s pose_runs=%s run_lengths=%s "
        "run_ranges=%s gaps=%s",
        session_id,
        len(pose_runs),
        [len(run) for run in pose_runs],
        [
            (run[0]["frame_index"], run[-1]["frame_index"])
            for run in pose_runs
        ],
        run_gaps,
    )

    for run_index, run in enumerate(pose_runs, start=1):
        if len(run) < 3:
            continue

        landmark_series = [entry["landmarks"] for entry in run]

        repetitions = segment_reps(landmark_series)

        logger.info(
            "[RepCount] session=%s run=%s frames=%s reps=%s",
            session_id,
            run_index,
            len(run),
            len(repetitions),
        )

        for repetition in repetitions:
            try:
                start_index = int(repetition["start"])
                bottom_index = int(repetition["bottom"])
                end_index = int(repetition["end"])
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"Invalid repetition boundaries: {repetition}"
                ) from exc

            if not (0 <= start_index <= bottom_index <= end_index < len(run)):
                raise RuntimeError(f"Invalid repetition range: {repetition}")

            rep_entries = run[start_index : end_index + 1]

            if rep_entries:
                repetition_entries.append(
                    {
                        "entries": rep_entries,
                        "key_frame_index": rep_entries[bottom_index - start_index][
                            "frame_index"
                        ],
                    }
                )

    if not repetition_entries:
        raise RuntimeError("No complete squat repetitions were detected.")

    return repetition_entries

def _prepare_assessments(
    session: AssessmentSession,
    repetition_entries: list[dict[str, Any]],
    thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    prepared_assessments: list[dict[str, Any]] = []

    for rep_number, rep_entry in enumerate(
        repetition_entries,
        start=1,
    ):
        entries = rep_entry["entries"]
        frame_width = next(
            (int(entry["source_width"]) for entry in entries if entry.get("source_width")),
            1280,
        )
        frame_height = next(
            (int(entry["source_height"]) for entry in entries if entry.get("source_height")),
            720,
        )
        native_fps = next(
            (float(entry["native_fps"]) for entry in entries if entry.get("native_fps")),
            30.0,
        )
        analysis_result = {
            "view_angle": session.view_angle,
            "frame_metadata": [
                {
                    key: entry.get(key)
                    for key in ("frame_index", "timestamp_ms")
                    if entry.get(key) is not None
                }
                for entry in entries
            ],
        }

        reference_template = reference_template_from_profile(
            session.body_profile,
            session.view_angle,
            next(
                (
                    entry.get("landmarks")
                    for entry in entries
                    if entry.get("frame_index") == rep_entry["key_frame_index"]
                ),
                entries[len(entries) // 2].get("landmarks") if entries else None,
            ),
        )
        if reference_template is not None and session.view_angle != "frontal":
            analysis_result["reference_template"] = reference_template

        model_prediction = {
            "status": "not_assessed",
            "reason": None,
        }

        if session.view_angle != "frontal":
            analysis_result["fppa"] = {
                "status": "not_assessed",
                "reason": "view_not_supported",
            }
            model_prediction["reason"] = "view_not_supported"
        else:
            try:
                fppa_features, fppa_metadata = extract_fppa_features(
                    entries,
                    frame_width=frame_width,
                    frame_height=frame_height,
                    native_fps=native_fps,
                )
                if not fppa_metadata.get("valid") or fppa_features is None:
                    analysis_result["fppa"] = {
                        "status": "not_assessed",
                        **fppa_metadata,
                    }
                    model_prediction["reason"] = fppa_metadata.get("reason")
                else:
                    analysis_result["fppa"] = {
                        **evaluate_fppa(fppa_features),
                        **fppa_metadata,
                    }
                    classifications = {}
                    for side in ("left", "right"):
                        knee = analysis_result["fppa"]["knees"][side]
                        if knee["state"] == "deviation":
                            key = (
                                "varus"
                                if knee["direction"] == "outward"
                                else f"valgus_{side}"
                            )
                            classifications[key] = {
                                "classification": "present",
                                "evaluation": {
                                    "difference": max(
                                        0.0,
                                        abs(knee["peak_degrees"])
                                        - analysis_result["fppa"]["cutoff_degrees"],
                                    )
                                },
                            }
                    analysis_result["classifications"] = classifications
                    model_prediction = predict_with_active_model(
                        features=fppa_features,
                        view_angle=session.view_angle,
                        prediction_target="knee_alignment",
                        feature_schema_version=FPPA_SCHEMA_VERSION,
                    )
            except (FeatureExtractionError, ValueError, TypeError) as exc:
                model_prediction = {
                    "status": "not_assessed",
                    "reason": "feature_extraction_failed",
                    "detail": str(exc),
                }
            except ModelInferenceError as exc:
                model_prediction = {
                    "status": "not_assessed",
                    "reason": "model_inference_failed",
                    "detail": str(exc),
                    **exc.payload,
                }

        if not session.view_angle:
            model_prediction["reason"] = "missing_view_angle"

        analysis_result["model_prediction"] = model_prediction

        prepared_assessments.append(
            {
                "rep_number": rep_number,
                "landmark_series": entries,
                "asymmetry_series": analysis_result.get("asymmetry_series"),
                "start_frame": entries[0]["frame_index"],
                "end_frame": entries[-1]["frame_index"],
                "key_frame_index": rep_entry["key_frame_index"],
                "analysis_result": analysis_result,
            }
        )

    return prepared_assessments

def _save_assessments(
    session: AssessmentSession,
    prepared_assessments: list[dict[str, Any]],
) -> None:
    with transaction.atomic():
        RepAssessment.objects.filter(session=session).delete()

        for assessment in prepared_assessments:
            RepAssessment.objects.create(
                session=session,
                rep_number=assessment["rep_number"],
                landmark_series=assessment["landmark_series"],
                asymmetry_series=assessment["asymmetry_series"],
                start_frame=assessment["start_frame"],
                end_frame=assessment["end_frame"],
                key_frame_index=assessment["key_frame_index"],
                analysis_result=assessment["analysis_result"],
            )

    logger.info(
        "[RepCount] session=%s saved_reps=%s",
        session.pk,
        len(prepared_assessments),
    )

def _generate_session_report(
    session: AssessmentSession,
    thresholds: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        return build_session_report(
            session.reps.all(),
            thresholds,
        )
    except Exception:
        logger.exception(
            "Session report generation failed for session=%s",
            session.pk,
        )
        return None

def process_assessment_session(session: AssessmentSession) -> None:
    session.status = AssessmentSession.Status.PROCESSING
    session.error_message = ""
    session.report = None

    session.save(
        update_fields=[
            "status",
            "error_message",
            "report",
        ],
    )

    try:
        result = VideoProcessor.process_video(
            session.video_file.path,
        )

        if result.get("status") != "success":
            raise ValueError(result.get("message", "Video processing failed."))

        landmark_data = result.get("landmark_data", [])

        if not landmark_data:
            raise RuntimeError("No landmark frames were produced from the video.")

        valid_pose_frames = sum(
            bool(entry.get("landmarks")) for entry in landmark_data
        )
        logger.info(
            "[RepCount] session=%s extraction=%s sampled=%s valid_pose=%s "
            "valid_pct=%.1f fps=%s source_resolution=%sx%s",
            session.pk,
            result.get("status"),
            len(landmark_data),
            valid_pose_frames,
            valid_pose_frames / len(landmark_data) * 100,
            result.get("native_fps"),
            result.get("source_width"),
            result.get("source_height"),
        )

        if valid_pose_frames == 0:
            raise RuntimeError(
                "Pose extraction failed: no valid pose landmarks were detected."
            )

        native_fps = float(result.get("native_fps") or 30.0)

        if not np.isfinite(native_fps) or native_fps <= 0:
            native_fps = 30.0

        expected_frame_step = max(
            1,
            round(native_fps / 30.0),
        )

        repetition_entries = _collect_repetition_entries(
            session_id=session.pk,
            landmark_data=landmark_data,
            expected_frame_step=expected_frame_step,
        )

        thresholds = session.exercise_variant.get_thresholds()

        prepared_assessments = _prepare_assessments(
            session,
            repetition_entries,
            thresholds,
        )

        _save_assessments(
            session,
            prepared_assessments,
        )

        session.report = _generate_session_report(
            session,
            thresholds,
        )

        session.status = AssessmentSession.Status.COMPLETED
        session.error_message = ""

    except Exception as exc:
        logger.exception(
            "Assessment processing failed for session=%s",
            session.pk,
        )

        # A failed run must not expose stale or partially written reps.
        RepAssessment.objects.filter(session=session).delete()

        session.status = AssessmentSession.Status.FAILED
        session.error_message = str(exc)
        session.report = None

    finally:
        session.processed_at = timezone.now()

        session.save(
            update_fields=[
                "status",
                "error_message",
                "processed_at",
                "report",
            ],
        )
