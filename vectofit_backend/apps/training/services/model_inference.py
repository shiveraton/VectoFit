from math import isfinite
from time import perf_counter

import numpy as np
from xgboost.core import XGBoostError

from apps.analytics.services.feature_schemas import schema_for_target

from ..models import ModelRegistry, TrainingJob
from .trainer import load_model

_MODEL_CACHE = {}
_MODEL_CACHE_LIMIT = 8


class ModelInferenceError(Exception):
    def __init__(self, detail: str, status_code: int = 409, **extra):
        super().__init__(detail)
        self.status_code = status_code
        self.payload = {"detail": detail, **extra}


def _load_cached_model(registry_entry):
    artifact = registry_entry.artifact
    cache_key = (
        registry_entry.pk,
        artifact.name,
        artifact.size,
        artifact.storage.get_modified_time(artifact.name),
    )
    estimator = _MODEL_CACHE.get(cache_key)
    if estimator is not None:
        return estimator, 0.0

    started = perf_counter()
    with artifact.open("rb") as model_file:
        estimator = load_model(model_file.read())
    loading_ms = (perf_counter() - started) * 1000

    if len(_MODEL_CACHE) >= _MODEL_CACHE_LIMIT:
        oldest_key = next(iter(_MODEL_CACHE))
        _MODEL_CACHE.pop(oldest_key)
    _MODEL_CACHE[cache_key] = estimator
    return estimator, loading_ms


def predict_with_active_model(
    *,
    features: dict,
    view_angle: str,
    prediction_target: str = "binary_form",
    model_name: str = "vectofit-squat-classifier",
    feature_schema_version: str | None = None,
) -> dict:
    expected_schema = schema_for_target(prediction_target).version
    feature_schema_version = feature_schema_version or expected_schema
    if feature_schema_version != expected_schema:
        raise ModelInferenceError(
            "Feature schema mismatch.",
            expected=expected_schema,
            received=feature_schema_version,
        )

    candidates = (
        ModelRegistry.objects.select_related("training_job")
        .filter(
            name=model_name,
            is_active=True,
            training_job__status=TrainingJob.Status.COMPLETED,
            training_job__view_angle=view_angle,
            training_job__prediction_target=prediction_target,
        )
        .order_by("-created_at")
    )

    candidates = list(candidates[:2])
    if not candidates:
        raise ModelInferenceError(
            "No active registered model matches this angle and prediction target.",
            status_code=404,
        )

    if len(candidates) > 1:
        raise ModelInferenceError(
            "More than one active model matches this configuration. "
            "Deactivate duplicates in the registry."
        )

    return predict_with_model(
        candidates[0],
        features=features,
        feature_schema_version=feature_schema_version,
    )


def predict_with_model(
    registry_entry, *, features: dict, feature_schema_version: str
) -> dict:
    job = registry_entry.training_job
    prediction_target = job.prediction_target
    schema = schema_for_target(prediction_target)

    if job.status != TrainingJob.Status.COMPLETED:
        raise ModelInferenceError("The selected model has not completed training.")

    if feature_schema_version != schema.version:
        raise ModelInferenceError(
            "Feature schema mismatch.",
            expected=schema.version,
            received=feature_schema_version,
        )

    if job.feature_schema_version != feature_schema_version:
        raise ModelInferenceError(
            "Model feature schema does not match the request.",
            expected=job.feature_schema_version,
            received=feature_schema_version,
        )

    expected_features = list(job.feature_selection or [])
    if not expected_features:
        raise ModelInferenceError("The selected model has no recorded features.")

    duplicate_features = len(expected_features) != len(set(expected_features))
    unknown_features = set(expected_features) - set(schema.feature_order)
    if duplicate_features or unknown_features:
        raise ModelInferenceError(
            "The selected model has an invalid feature selection."
        )

    if not registry_entry.artifact:
        raise ModelInferenceError("The selected model has no model artifact.")

    missing = [name for name in expected_features if name not in features]
    if missing:
        raise ModelInferenceError(
            "Required model features are missing.",
            status_code=400,
            missing_features=missing,
            expected_features=expected_features,
        )

    vector_started = perf_counter()

    try:
        vector = [float(features[name]) for name in expected_features]
    except (TypeError, ValueError) as exc:
        raise ModelInferenceError(
            "Model features must be numeric values.",
            status_code=400,
        ) from exc

    if not all(isfinite(value) for value in vector):
        raise ModelInferenceError(
            "Model features must be finite numbers.",
            status_code=400,
        )

    vector_ms = (perf_counter() - vector_started) * 1000

    try:
        estimator, model_loading_ms = _load_cached_model(registry_entry)

        prediction_started = perf_counter()
        matrix = np.asarray([vector], dtype=float)

        predictions = np.asarray(estimator.predict(matrix))
        probabilities_raw = np.asarray(
            estimator.predict_proba(matrix),
            dtype=float,
        )[0]
        predicted_index = int(predictions.reshape(-1)[0])

        inference_ms = vector_ms + (perf_counter() - prediction_started) * 1000

    except (OSError, ValueError, AttributeError, IndexError, XGBoostError) as exc:
        raise ModelInferenceError(
            f"Model inference failed: {exc}",
            status_code=500,
        ) from exc

    mapping = (
        (job.training_manifest or {}).get("class_mapping")
        or (job.metrics or {}).get("class_mapping")
        or {}
    )

    class_keys = [str(index) for index in range(len(probabilities_raw))]
    if not isinstance(mapping, dict) or any(
        not isinstance(mapping.get(key), str) or not mapping[key].strip()
        for key in class_keys
    ):
        raise ModelInferenceError(
            "The selected model has a missing or incomplete class mapping."
        )

    if str(predicted_index) not in class_keys:
        raise ModelInferenceError("The selected model returned an invalid class index.")

    predicted_class = mapping[str(predicted_index)]
    class_probabilities = {
        mapping[str(index)]: float(probability)
        for index, probability in enumerate(probabilities_raw)
    }

    response = {
        "status": "assessed",
        "model_id": registry_entry.pk,
        "model_name": registry_entry.name,
        "model_version": registry_entry.version,
        "view_angle": job.view_angle,
        "prediction_target": job.prediction_target,
        "feature_schema_version": job.feature_schema_version,
        "predicted_class": predicted_class,
        "probability": (
            float(probabilities_raw[predicted_index])
            if 0 <= predicted_index < len(probabilities_raw)
            else None
        ),
        "class_probabilities": class_probabilities,
        "model_loading_ms": model_loading_ms,
        "inference_ms": inference_ms,
    }

    if prediction_target == TrainingJob.PredictionTarget.BINARY_FORM:
        normalized = str(predicted_class).strip().casefold().replace("-", "_")
        binary_labels = {
            "good": True,
            "good_form": True,
            "bad": False,
            "bad_form": False,
        }
        if normalized not in binary_labels:
            response.update(
                {
                    "status": "not_assessed",
                    "reason": "unsupported_class_label",
                    "detail": (
                        "The selected binary-form model returned an unsupported "
                        f"class label: {predicted_class!r}."
                    ),
                    "is_correct": None,
                }
            )
        else:
            response["is_correct"] = binary_labels[normalized]
    elif prediction_target == TrainingJob.PredictionTarget.ERROR_TYPE:
        response["is_correct"] = (
            str(predicted_class).strip().casefold() == "correct_form"
        )

    return response
