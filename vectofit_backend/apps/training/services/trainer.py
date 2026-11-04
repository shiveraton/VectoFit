import os
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
from xgboost import XGBClassifier

from .data_loader import SampleSet, group_split

BASELINE_HYPERPARAMETERS = {
    "n_estimators": 200,
    "max_depth": 4,
    "learning_rate": 0.1,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "min_child_weight": 1,
    "reg_lambda": 1.0,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
}


class InsufficientDataError(Exception):
    """Raised when the data cannot support a valid train/test experiment."""


def resolve_hyperparameters(
    overrides=None, prediction_target="binary_form", class_count=2
):
    params = dict(BASELINE_HYPERPARAMETERS)
    if overrides:
        unknown = set(overrides) - set(BASELINE_HYPERPARAMETERS)
        if unknown:
            raise ValueError(
                f"Unsupported hyperparameter(s): {sorted(unknown)}. "
                f"Allowed: {sorted(BASELINE_HYPERPARAMETERS)}"
            )
        params.update(overrides)

    if prediction_target == "error_type":
        if class_count < 2:
            raise InsufficientDataError(
                "error_type training requires at least two target classes."
            )
        params["objective"] = "multi:softprob"
        params["eval_metric"] = "mlogloss"
        params["num_class"] = class_count
    else:
        params["objective"] = "binary:logistic"
        params["eval_metric"] = str(params.get("eval_metric") or "logloss")
        params.pop("num_class", None)
    return params


def _check_split_viability(train_idx, test_idx, labels):
    if not train_idx or not test_idx:
        raise InsufficientDataError(
            "The participant-grouped split produced an empty train or test set. "
            "Record repetitions from at least two distinct participants."
        )

    target_classes = set(labels)
    train_classes = {labels[i] for i in train_idx}
    test_classes = {labels[i] for i in test_idx}
    if train_classes != target_classes:
        raise InsufficientDataError(
            "The training split does not contain every target class. Add labelled "
            "repetitions for the missing class across more participants."
        )
    if test_classes != target_classes:
        raise InsufficientDataError(
            "The held-out test split does not contain every target class. Add data "
            "from more participants so every class can be evaluated without leakage."
        )
    if set(train_idx) & set(test_idx):
        raise InsufficientDataError(
            "Data leakage detected between training and test sample indices."
        )


def train_and_evaluate(sample_set, hyperparameters=None, test_size=0.3, seed=42):
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

    train_idx, test_idx = group_split(sample_set.groups, test_size, seed, labels=labels)
    _check_split_viability(train_idx, test_idx, labels)

    params = resolve_hyperparameters(
        hyperparameters,
        prediction_target=sample_set.prediction_target,
        class_count=len(target_names),
    )
    model = XGBClassifier(**params, random_state=seed)
    model.fit(X[train_idx], y[train_idx])
    y_pred = model.predict(X[test_idx]).astype(int)
    probabilities = model.predict_proba(X[test_idx])
    class_indices = list(range(len(target_names)))
    averaging = "binary" if sample_set.prediction_target == "binary_form" else "macro"
    metrics = {
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
    return {
        "model": model,
        "metrics": metrics,
        "train_idx": train_idx,
        "test_idx": test_idx,
        "feature_names": list(sample_set.feature_names),
        "hyperparameters": params,
        "seed": seed,
        "target_names": target_names,
        "class_mapping": metrics["class_mapping"],
    }


def lopo_evaluate(sample_set, hyperparameters=None, seed=42):
    labels = np.asarray([{"bad": 0, "good": 1}[label] for label in sample_set.labels])
    groups = np.asarray(sample_set.groups)
    X = np.asarray(sample_set.rows, dtype=float)
    predictions = np.full(len(labels), -1, dtype=int)
    params = resolve_hyperparameters(
        hyperparameters,
        prediction_target="knee_alignment",
        class_count=2,
    )
    for participant in sorted(set(groups)):
        test_idx = np.flatnonzero(groups == participant)
        train_idx = np.flatnonzero(groups != participant)
        if set(labels[train_idx]) != {0, 1}:
            raise InsufficientDataError(
                f"LOPO participant {participant!r} leaves one class out of training."
            )
        model = XGBClassifier(**params, random_state=seed)
        model.fit(X[train_idx], labels[train_idx])
        predictions[test_idx] = model.predict(X[test_idx]).astype(int)
    return _lopo_metrics(labels, predictions, groups)


def _lopo_metrics(labels, predictions, groups):
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
                        labels=[0, 1],
                        average="macro",
                        zero_division=0,
                    )
                ),
                "sample_count": int(len(indices)),
            }
        )
    return {
        "macro_f1": float(
            f1_score(labels, predictions, labels=[0, 1], average="macro", zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
        "per_participant": per_participant,
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
