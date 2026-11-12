import os
import platform
from importlib.metadata import version
import tempfile

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from xgboost import DMatrix, XGBClassifier, train

from ..config import (
    TARGET_TASK_PROFILES, locked_hyperparameters,
    validate_hyperparameters,
)
from .data_loader import SampleSet


def training_environment():
    return {
        "python": platform.python_version(),
        **{package: version(package) for package in ("xgboost", "scikit-learn", "numpy", "scipy")},
    }


class InsufficientDataError(Exception):
    """Raised when the data cannot support a valid train/test experiment."""


def resolve_hyperparameters(
    overrides=None, prediction_target="binary_form", class_count=2
):
    return {
        **validate_hyperparameters(overrides or {}),
        **locked_hyperparameters(prediction_target, class_count),
    }


def scale_pos_weight(labels):
    positive_count = int(np.sum(labels == 1))
    return float(np.sum(labels == 0) / positive_count) if positive_count else 1.0


def train_and_evaluate(sample_set, hyperparameters=None):
    if not isinstance(sample_set, SampleSet):
        raise TypeError("train_and_evaluate expects a SampleSet.")

    raw_labels = list(sample_set.labels)
    if sample_set.prediction_target == "binary_form":
        allowed = {0, 1}
        if not set(raw_labels).issubset(allowed):
            raise InsufficientDataError(
                "binary_form targets must be encoded as 0 or 1."
            )
        if set(raw_labels) != {0, 1}:
            raise InsufficientDataError(
                "binary_form training requires both target classes: incorrect (0) "
                "and correct (1). Add labelled repetitions from both classes."
            )
        target_names = ["BAD_FORM", "GOOD_FORM"]
        label_to_index = {0: 0, 1: 1}
        labels = [label_to_index[label] for label in raw_labels]
    elif sample_set.prediction_target == "error_type":
        target_names = sorted({str(label) for label in raw_labels})
        if len(target_names) < 2:
            raise InsufficientDataError(
                "error_type requires at least two distinct target classes."
            )
        label_to_index = {name: index for index, name in enumerate(target_names)}
        labels = [label_to_index[str(label)] for label in raw_labels]
    elif sample_set.prediction_target == "knee_alignment":
        if set(raw_labels) != {"good", "bad"}:
            raise InsufficientDataError(
                "knee_alignment requires both good and bad target classes."
            )
        target_names = ["bad", "good"]
        label_to_index = {"bad": 0, "good": 1}
        labels = [label_to_index[label] for label in raw_labels]
    else:
        raise InsufficientDataError(
            f"Unsupported prediction target {sample_set.prediction_target!r}."
        )

    X = np.asarray(sample_set.rows, dtype=float)
    y = np.asarray(labels, dtype=int)
    if X.ndim != 2 or X.shape[1] != len(sample_set.feature_names):
        raise InsufficientDataError(
            f"Design matrix shape {X.shape} does not match {len(sample_set.feature_names)} selected features."
        )
    if len(X) != len(y) or len(y) != len(sample_set.groups):
        raise InsufficientDataError(
            "Feature rows, target labels, and participant groups are misaligned."
        )
    if not np.all(np.isfinite(X)):
        raise InsufficientDataError(
            "The design matrix contains non-finite values; refusing to train."
        )

    groups = np.asarray(sample_set.groups)
    if len(set(groups)) < 2:
        raise InsufficientDataError("LOPO requires at least two distinct participants.")
    params = resolve_hyperparameters(
        hyperparameters,
        prediction_target=sample_set.prediction_target,
        class_count=len(target_names),
    )
    task_profile = TARGET_TASK_PROFILES[sample_set.prediction_target]
    y_pred = np.full(len(y), -1, dtype=int)
    probabilities = np.zeros((len(y), len(target_names)), dtype=float)
    folds = []
    for participant in sorted(set(groups)):
        test_indices = np.flatnonzero(groups == participant)
        train_indices = np.flatnonzero(groups != participant)
        fold = {
            "participant": str(participant),
            "train_idx": train_indices.tolist(),
            "test_idx": test_indices.tolist(),
        }
        if task_profile == "quality":
            if set(y[train_indices]) != {0, 1}:
                raise InsufficientDataError(
                    f"LOPO participant {participant!r} leaves one class out of training."
                )
            weight = scale_pos_weight(y[train_indices])
            fold_model = XGBClassifier(**params, scale_pos_weight=weight)
            fold_model.fit(X[train_indices], y[train_indices])
            probabilities[test_indices] = fold_model.predict_proba(X[test_indices])
            fold["scale_pos_weight"] = weight
        else:
            native_params = {name: value for name, value in params.items() if name != "n_estimators"}
            fold_model = train(
                native_params,
                DMatrix(X[train_indices], label=y[train_indices]),
                num_boost_round=params["n_estimators"],
            )
            probabilities[test_indices] = fold_model.predict(DMatrix(X[test_indices]))
        y_pred[test_indices] = probabilities[test_indices].argmax(axis=1)
        folds.append(fold)

    final_params = dict(params)
    if task_profile == "quality":
        final_params["scale_pos_weight"] = scale_pos_weight(y)
    model = XGBClassifier(**final_params)
    model.fit(X, y)
    train_idx = test_idx = list(range(len(y)))
    class_indices = list(range(len(target_names)))
    averaging = "binary" if sample_set.prediction_target == "binary_form" else "macro"
    metrics = {
        "evaluation_method": "leave_one_participant_out",
        "fold_count": len(folds),
        "averaging": averaging,
        "train_participant_count": len(set(groups)) - 1,
        "test_participant_count": 1,
        "accuracy": float(accuracy_score(y[test_idx], y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y[test_idx], y_pred)),
        "f1": float(f1_score(y[test_idx], y_pred, average=averaging, zero_division=0)),
        "precision": float(
            precision_score(y[test_idx], y_pred, average=averaging, zero_division=0)
        ),
        "recall": float(
            recall_score(y[test_idx], y_pred, average=averaging, zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(
            y[test_idx], y_pred, labels=class_indices
        ).tolist(),
        "classification_report": classification_report(
            y[test_idx],
            y_pred,
            labels=class_indices,
            target_names=target_names,
            zero_division=0,
        ),
        "target_names": target_names,
        "class_mapping": {str(index): name for index, name in enumerate(target_names)},
        "prediction_target": sample_set.prediction_target,
        "train_class_distribution": _distribution(y[train_idx], target_names),
        "test_class_distribution": _distribution(y[test_idx], target_names),
        "overall_class_distribution": _distribution(y, target_names),
        "feature_names": list(sample_set.feature_names),
        "feature_importances": {
            name: float(value)
            for name, value in zip(sample_set.feature_names, model.feature_importances_)
        },
        "held_out_probabilities": [
            {target_names[i]: float(prob) for i, prob in enumerate(row)}
            for row in probabilities
        ],
    }
    metrics.update(_lopo_metrics(y, y_pred, groups, class_indices))
    for row, sample_id in zip(metrics["oof_predictions"], sample_set.sample_ids):
        row["sample_id"] = sample_id
    return {
        "model": model,
        "metrics": metrics,
        "train_idx": train_idx,
        "test_idx": test_idx,
        "feature_names": list(sample_set.feature_names),
        "hyperparameters": params,
        "seed": params["seed"],
        "folds": folds,
        "final_scale_pos_weight": final_params.get("scale_pos_weight"),
        "task_profile": task_profile,
        "target_names": target_names,
        "class_mapping": metrics["class_mapping"],
    }


def lopo_evaluate(sample_set, hyperparameters=None):
    result = train_and_evaluate(sample_set, hyperparameters)
    metrics = result["metrics"]
    metrics.update({
        "hyperparameters": result["hyperparameters"],
        "seed": result["seed"],
        "folds": result["folds"],
    })
    return metrics


def _lopo_metrics(labels, predictions, groups, class_indices):
    per_participant = []
    for participant in sorted(set(groups)):
        indices = np.flatnonzero(groups == participant)
        per_participant.append(
            {
                "participant": str(participant),
                "macro_f1": float(
                    f1_score(
                        labels[indices],
                        predictions[indices],
                        labels=class_indices,
                        average="macro",
                        zero_division=0,
                    )
                ),
                "sample_count": int(len(indices)),
            }
        )
    return {
        "macro_f1": float(
            f1_score(labels, predictions, labels=class_indices, average="macro", zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=class_indices).tolist(),
        "per_participant": per_participant,
        "oof_predictions": [
            {
                "participant": str(group),
                "label": int(label),
                "prediction": int(prediction),
            }
            for group, label, prediction in zip(groups, labels, predictions)
        ],
    }


def _distribution(values, target_names):
    return {
        target_names[int(label)]: int(np.sum(values == label))
        for label in np.unique(values)
    }


def serialize_model(model):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_path = temp_file.name
        model.save_model(temp_path)
        with open(temp_path, "rb") as file:
            return file.read()
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def load_model(artifact):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(artifact)
        estimator = XGBClassifier()
        estimator.load_model(temp_path)
        return estimator
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
