import math
from time import perf_counter

import cv2
from django.utils import timezone

from apps.analytics.services.fppa import (
    FEATURE_SCHEMA_VERSION,
    M1_FEATURES,
    extract_fppa_features,
)
from apps.analytics.services.schemav1.features import FeatureExtractionError
from apps.assessments.services.repetition_extractor import collect_repetition_entries
from apps.assessments.services.video_processor import VideoProcessor

from ..models import InferenceStatus, TrainingJob
from .model_inference import predict_with_model

MAX_VIDEO_BYTES = 200 * 1024 * 1024
MAX_VIDEO_SECONDS = 300


def validate_simulation_model(model):
    job = model.training_job
    if (
        job.status != TrainingJob.Status.COMPLETED
        or job.view_angle != "frontal"
        or job.prediction_target != "knee_alignment"
        or job.feature_schema_version != FEATURE_SCHEMA_VERSION
    ):
        raise ValueError("Choose a completed frontal FPPA v2 knee-alignment model.")
    features = job.feature_selection or []
    if (
        not features
        or len(features) != len(set(features))
        or set(features) - set(M1_FEATURES)
    ):
        raise ValueError("The model has an invalid recorded feature selection.")
    if not model.artifact or not model.artifact.storage.exists(model.artifact.name):
        raise ValueError("The model artifact is unavailable.")


def model_snapshot(model):
    return {
        "id": model.pk,
        "name": model.name,
        "version": model.version,
        "features": list(model.training_job.feature_selection),
        "feature_schema_version": model.training_job.feature_schema_version,
    }


def prepare_simulation(simulation):
    started = perf_counter()
    path = simulation.video_file.path
    capture = cv2.VideoCapture(path)
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not capture.isOpened() or not math.isfinite(fps) or fps <= 0:
            raise ValueError(
                "The video could not be decoded or has invalid frame timing."
            )
        if not math.isfinite(frames) or frames <= 0:
            raise ValueError("The video contains no readable frames.")
        if frames / fps > MAX_VIDEO_SECONDS:
            raise ValueError("Videos must be five minutes or shorter.")
    finally:
        capture.release()

    result = VideoProcessor.process_video(path)
    if result.get("status") != "success":
        raise ValueError(result.get("message") or "Video processing failed.")
    repetitions = collect_repetition_entries(
        session_id=simulation.pk,
        landmark_data=result["landmark_data"],
        expected_frame_step=result["sample_step"],
    )
    prepared = []
    for number, repetition in enumerate(repetitions, start=1):
        entries = repetition["entries"]
        try:
            features, metadata = extract_fppa_features(
                entries,
                frame_width=result["coordinate_width"],
                frame_height=result["coordinate_height"],
                native_fps=result["native_fps"],
                sample_step=result["sample_step"],
            )
            if features and not all(
                math.isfinite(value) for value in features.values()
            ):
                features = None
                metadata = {"valid": False, "reason": "non_finite_features"}
        except (FeatureExtractionError, ValueError, TypeError):
            features = None
            metadata = {"valid": False, "reason": "feature_extraction_failed"}
        prepared.append(
            {
                "rep_number": number,
                "start_ms": float(entries[0]["timestamp_ms"]),
                "end_ms": float(entries[-1]["timestamp_ms"]),
                "valid": bool(metadata.get("valid") and features),
                "reason": metadata.get("reason"),
                "features": features or {},
            }
        )
    simulation.repetitions = prepared
    simulation.feature_schema_version = FEATURE_SCHEMA_VERSION
    simulation.preprocessing_ms = (perf_counter() - started) * 1000
    simulation.status = InferenceStatus.COMPLETED
    simulation.error_message = ""
    simulation.completed_at = timezone.now()
    simulation.save()


def run_simulation_model(run):
    if run.model is None:
        raise ValueError("The selected model was deleted. Choose another model.")
    validate_simulation_model(run.model)
    predictions = []
    loading_ms = 0.0
    inference_ms = 0.0
    for repetition in run.simulation.repetitions:
        if not repetition["valid"]:
            predictions.append(
                {
                    "rep_number": repetition["rep_number"],
                    "status": "not_assessed",
                    "reason": repetition["reason"] or "invalid_features",
                }
            )
            continue
        result = predict_with_model(
            run.model,
            features=repetition["features"],
            feature_schema_version=run.simulation.feature_schema_version,
        )
        predictions.append({"rep_number": repetition["rep_number"], **result})
        loading_ms += result["model_loading_ms"]
        inference_ms += result["inference_ms"]
    run.predictions = predictions
    run.model_snapshot = model_snapshot(run.model)
    run.model_loading_ms = loading_ms
    run.inference_ms = inference_ms
    run.status = InferenceStatus.COMPLETED
    run.error_message = ""
    run.completed_at = timezone.now()
    run.save()
