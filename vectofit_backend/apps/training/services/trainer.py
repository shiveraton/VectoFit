"""XGBoost training and held-out evaluation.

This module is deliberately free of Django request handling and of view logic
so that it can be driven equally from the REST API (synchronous, for the first
working experiment) and from a Celery task later without duplicating the
training logic.

It never invents a score: metrics come only from predictions made on a test
set that the model was not fitted on, and if that split is impossible the
function raises rather than reporting a number that would be meaningless.
"""

import io

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

#: Deliberately plain baseline. Hyperparameter tuning is explicitly deferred
#: until there is a reproducible baseline to compare against.
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


def resolve_hyperparameters(overrides=None):
    """Merge caller-supplied hyperparameters over the baseline."""
    params = dict(BASELINE_HYPERPARAMETERS)
    if overrides:
        unknown = set(overrides) - set(BASELINE_HYPERPARAMETERS)
        if unknown:
            raise ValueError(
                f"Unsupported hyperparameter(s): {sorted(unknown)}. "
                f"Allowed: {sorted(BASELINE_HYPERPARAMETERS)}"
            )
        params.update(overrides)
    return params


def _check_split_viability(sample_set, train_idx, test_idx, labels):
    """Refuse to evaluate on a split that cannot be scientifically trusted."""
    if not train_idx or not test_idx:
        raise InsufficientDataError(
            "The group split produced an empty train or test set. This happens "
            "when every repetition comes from a single video/session, so no "
            "leakage-free held-out split exists. Record repetitions from at "
            "least two separate sessions before training."
        )

    train_classes = {labels[i] for i in train_idx}
    test_classes = {labels[i] for i in test_idx}

    if len(train_classes) < 2:
        raise InsufficientDataError(
            "The training split contains only one class, so a classifier "
            "cannot be fitted. Add labelled repetitions of both correct and "
            "incorrect form."
        )

    if len(test_classes) < 2:
        raise InsufficientDataError(
            "The held-out test split contains only one class, so accuracy and "
            "F1 are not meaningful. Record more sessions so that the split "
            "covers both classes, or accept that this run cannot be evaluated."
        )

    overlap = set(train_idx) & set(test_idx)
    if overlap:
        raise InsufficientDataError(
            f"Data leakage detected: {len(overlap)} sample(s) appear in both "
            f"the training and test splits."
        )


def train_and_evaluate(sample_set, hyperparameters=None, test_size=0.3, seed=42):
    """Fit a baseline XGBoost classifier and score it on held-out data.

    Returns a dict with the fitted estimator, the metrics, the split indices
    and the column names, ready for artifact persistence and API response.
    """
    if not isinstance(sample_set, SampleSet):
        raise TypeError("train_and_evaluate expects a SampleSet.")

    labels = [int(label) for label in sample_set.labels]
    X = np.asarray(sample_set.rows, dtype=float)
    y = np.asarray(labels, dtype=int)

    if X.ndim != 2 or X.shape[1] != len(sample_set.feature_names):
        raise InsufficientDataError(
            f"Design matrix shape {X.shape} does not match "
            f"{len(sample_set.feature_names)} selected features."
        )

    if not np.all(np.isfinite(X)):
        raise InsufficientDataError(
            "The design matrix contains non-finite values; refusing to train."
        )

    train_idx, test_idx = group_split(sample_set.groups, test_size, seed)
    _check_split_viability(sample_set, train_idx, test_idx, labels)

    params = resolve_hyperparameters(hyperparameters)

    model = XGBClassifier(
        **params,
        random_state=seed,
        eval_metric=params.get("eval_metric", "logloss"),
    )
    model.fit(X[train_idx], y[train_idx])

    y_pred = model.predict(X[test_idx])
    y_proba = model.predict_proba(X[test_idx])[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y[test_idx], y_pred)),
        "balanced_accuracy": float(
            balanced_accuracy_score(y[test_idx], y_pred)
        ),
        "f1": float(f1_score(y[test_idx], y_pred, zero_division=0)),
        "precision": float(
            precision_score(y[test_idx], y_pred, zero_division=0)
        ),
        "recall": float(recall_score(y[test_idx], y_pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(
            y[test_idx], y_pred, labels=[0, 1]
        ).tolist(),
        "classification_report": classification_report(
            y[test_idx], y_pred, labels=[0, 1], zero_division=0
        ),
        "train_class_distribution": _distribution(y[train_idx]),
        "test_class_distribution": _distribution(y[test_idx]),
        "overall_class_distribution": _distribution(y),
        "feature_names": list(sample_set.feature_names),
        "feature_importances": {
            name: float(value)
            for name, value in zip(
                sample_set.feature_names, model.feature_importances_
            )
        },
    }

    return {
        "model": model,
        "metrics": metrics,
        "train_idx": train_idx,
        "test_idx": test_idx,
        "feature_names": list(sample_set.feature_names),
        "hyperparameters": params,
        "seed": seed,
    }


def _distribution(values):
    """Class counts as a JSON-safe mapping."""
    return {
        str(int(label)): int(np.sum(values == label))
        for label in np.unique(values)
    }


def serialize_model(model):
    """Serialise the fitted estimator to bytes (XGBoost native JSON)."""
    buffer = io.BytesIO()
    model.save_model(buffer)
    return buffer.getvalue()


def load_model(artifact):
    """Rebuild an estimator from bytes produced by :func:`serialize_model`."""
    estimator = XGBClassifier()
    estimator.load_model(io.BytesIO(artifact))
    return estimator
