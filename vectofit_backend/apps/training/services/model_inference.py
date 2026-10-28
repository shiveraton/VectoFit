from math import isfinite

import numpy as np
from xgboost.core import XGBoostError

from apps.analytics.services.features import FEATURE_SCHEMA_VERSION

from ..models import ModelRegistry, TrainingJob
from .trainer import load_model


class ModelInferenceError(Exception):
    def __init__(self, detail: str, status_code: int = 409, **extra):
        super().__init__(detail)
        self.status_code = status_code
        self.payload = {"detail": detail, **extra}


def predict_with_active_model(
    *,
    features: dict,
    view_angle: str,
    prediction_target: str = "binary_form",
    model_name: str = "vectofit-squat-classifier",
    feature_schema_version: str = FEATURE_SCHEMA_VERSION,
) -> dict:
    if feature_schema_version != FEATURE_SCHEMA_VERSION:
        raise ModelInferenceError(
            "Feature schema mismatch.",
            expected=FEATURE_SCHEMA_VERSION,
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

    if not candidates.exists():
        raise ModelInferenceError(
            "No active registered model matches this angle and prediction target.",
            status_code=404,
        )

    if candidates.count() > 1:
        raise ModelInferenceError(
            "More than one active model matches this configuration. "
            "Deactivate duplicates in the registry."
        )

    registry_entry = candidates.first()
    job = registry_entry.training_job

    if job.feature_schema_version != feature_schema_version:
        raise ModelInferenceError(
            "Model feature schema does not match the request.",
            expected=job.feature_schema_version,
            received=feature_schema_version,
        )

    expected_features = list(job.feature_selection or [])
    if not expected_features:
        raise ModelInferenceError("The active model has no recorded feature schema.")

    if not registry_entry.artifact:
        raise ModelInferenceError("The active registry entry has no model artifact.")

    missing = [name for name in expected_features if name not in features]
    if missing:
        raise ModelInferenceError(
            "Required model features are missing.",
            status_code=400,
            missing_features=missing,
            expected_features=expected_features,
        )

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

    try:
        with registry_entry.artifact.open("rb") as model_file:
            estimator = load_model(model_file.read())

        predictions = np.asarray(estimator.predict(np.asarray([vector], dtype=float)))
        probabilities_raw = np.asarray(
            estimator.predict_proba(np.asarray([vector], dtype=float)),
            dtype=float,
        )[0]

        predicted_index = int(predictions.reshape(-1)[0])
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

    predicted_class = mapping.get(str(predicted_index), str(predicted_index))
    class_probabilities = {
        mapping.get(str(index), str(index)): float(probability)
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
                        "The active binary-form model returned an unsupported "
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
