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
    roc_auc_score,
)
from xgboost import XGBClassifier

from .data_loader import SampleSet, group_split, leave_one_participant_out_folds

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

EVALUATION_STRATEGIES = ("lopo", "holdout")
STRATEGY_NAMES = {
    "lopo": "leave_one_participant_out",
    "holdout": "group_by_participant",
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


def _distribution(values, target_names):
    values = np.asarray(values)
    return {
        target_names[int(label)]: int(np.sum(values == label))
        for label in np.unique(values)
    }


def _encode_targets(sample_set):
    raw_labels = list(sample_set.labels)
    if sample_set.prediction_target == "binary_form":
        if not set(raw_labels).issubset({0, 1}):
            raise InsufficientDataError(
                "binary_form targets must be encoded as 0 or 1."
            )
        if set(raw_labels) != {0, 1}:
            raise InsufficientDataError(
                "binary_form training requires both target classes: incorrect (0) "
                "and correct (1). Add labelled repetitions from both classes."
            )
        return ["BAD_FORM", "GOOD_FORM"], [int(label) for label in raw_labels]
    if sample_set.prediction_target == "error_type":
        target_names = sorted({str(label) for label in raw_labels})
        if len(target_names) < 2:
            raise InsufficientDataError(
                "error_type requires at least two distinct target classes."
            )
        mapping = {name: index for index, name in enumerate(target_names)}
        return target_names, [mapping[str(label)] for label in raw_labels]
    raise InsufficientDataError(
        f"Unsupported prediction target {sample_set.prediction_target!r}."
    )


def _score(y_true, y_pred, probabilities, target_names, prediction_target):
    class_indices = list(range(len(target_names)))
    averaging = "binary" if prediction_target == "binary_form" else "macro"
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, average=averaging, zero_division=0)),
        "precision": float(
            precision_score(y_true, y_pred, average=averaging, zero_division=0)
        ),
        "recall": float(
            recall_score(y_true, y_pred, average=averaging, zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(
            y_true, y_pred, labels=class_indices
        ).tolist(),
        "classification_report": classification_report(
            y_true,
            y_pred,
            labels=class_indices,
            target_names=target_names,
            zero_division=0,
        ),
    }
    if prediction_target == "binary_form" and len(np.unique(y_true)) == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_true, probabilities[:, 1]))
    return metrics


def _new_model(params, seed):
    return XGBClassifier(**params, random_state=seed)


def train_and_evaluate(
    sample_set, hyperparameters=None, test_size=0.3, seed=42, evaluation="lopo"
):
    if not isinstance(sample_set, SampleSet):
        raise TypeError("train_and_evaluate expects a SampleSet.")
    if evaluation not in EVALUATION_STRATEGIES:
        raise InsufficientDataError(
            f"evaluation must be one of {list(EVALUATION_STRATEGIES)}."
        )

    target_names, labels = _encode_targets(sample_set)
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

    params = resolve_hyperparameters(
        hyperparameters,
        prediction_target=sample_set.prediction_target,
        class_count=len(target_names),
    )
    if evaluation == "lopo":
        return _evaluate_lopo(sample_set, X, y, target_names, params, seed)
    return _evaluate_holdout(sample_set, X, y, target_names, params, test_size, seed)


def _finish_metrics(metrics, sample_set, target_names, y, eval_idx, train_dist_idx):
    metrics.update(
        {
            "target_names": target_names,
            "class_mapping": {
                str(index): name for index, name in enumerate(target_names)
            },
            "prediction_target": sample_set.prediction_target,
            "train_class_distribution": _distribution(y[train_dist_idx], target_names),
            "test_class_distribution": _distribution(y[eval_idx], target_names),
            "overall_class_distribution": _distribution(y, target_names),
            "feature_names": list(sample_set.feature_names),
        }
    )
    return metrics


def _evaluate_holdout(sample_set, X, y, target_names, params, test_size, seed):
    labels = y.tolist()
    train_idx, test_idx = group_split(sample_set.groups, test_size, seed, labels=labels)
    _check_split_viability(train_idx, test_idx, labels)

    model = _new_model(params, seed)
    model.fit(X[train_idx], y[train_idx])
    y_pred = model.predict(X[test_idx]).astype(int)
    probabilities = model.predict_proba(X[test_idx])
    metrics = _score(
        y[test_idx], y_pred, probabilities, target_names, sample_set.prediction_target
    )
    _finish_metrics(metrics, sample_set, target_names, y, test_idx, train_idx)
    metrics["feature_importances"] = {
        name: float(value)
        for name, value in zip(sample_set.feature_names, model.feature_importances_)
    }
    metrics["held_out_probabilities"] = [
        {target_names[i]: float(prob) for i, prob in enumerate(row)}
        for row in probabilities
    ]
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
        "evaluation": {
            "strategy": STRATEGY_NAMES["holdout"],
            "test_size": test_size,
        },
        "oof": None,
    }


def _evaluate_lopo(sample_set, X, y, target_names, params, seed):
    folds, skipped = leave_one_participant_out_folds(sample_set.groups, y.tolist())
    n_samples, n_classes = len(y), len(target_names)
    probabilities = np.full((n_samples, n_classes), np.nan)
    per_participant = {}

    for fold in folds:
        model = _new_model(params, seed)
        model.fit(X[fold["train_idx"]], y[fold["train_idx"]])
        fold_proba = model.predict_proba(X[fold["test_idx"]])
        probabilities[fold["test_idx"]] = fold_proba
        fold_pred = fold_proba.argmax(axis=1)
        fold_true = y[fold["test_idx"]]
        per_participant[fold["group"]] = {
            "n_reps": len(fold_true),
            "n_correct": int(np.sum(fold_pred == fold_true)),
            "accuracy": float(np.mean(fold_pred == fold_true)),
            "class_counts": _distribution(fold_true, target_names),
        }

    evaluated = np.flatnonzero(~np.isnan(probabilities[:, 0]))
    if set(y[evaluated].tolist()) != set(range(n_classes)):
        raise InsufficientDataError(
            "The pooled held-out predictions do not contain every target class; "
            "add data from more participants."
        )
    pooled_proba = probabilities[evaluated]
    pooled_pred = pooled_proba.argmax(axis=1)
    metrics = _score(
        y[evaluated],
        pooled_pred,
        pooled_proba,
        target_names,
        sample_set.prediction_target,
    )

    final_model = _new_model(params, seed)
    final_model.fit(X, y)
    _finish_metrics(
        metrics, sample_set, target_names, y, evaluated, np.arange(n_samples)
    )
    metrics["feature_importances"] = {
        name: float(value)
        for name, value in zip(
            sample_set.feature_names, final_model.feature_importances_
        )
    }
    oof_probabilities = [
        {target_names[i]: float(prob) for i, prob in enumerate(row)}
        for row in pooled_proba
    ]
    metrics["held_out_probabilities"] = oof_probabilities
    metrics["held_out_index"] = evaluated.tolist()

    evaluation = {
        "strategy": STRATEGY_NAMES["lopo"],
        "n_participants": len({fold["group"] for fold in folds}) + len(skipped),
        "n_folds": len(folds),
        "skipped_folds": skipped,
        "evaluated_samples": len(evaluated),
        "unevaluated_samples": int(n_samples - len(evaluated)),
        "per_participant": per_participant,
    }
    metrics["evaluation"] = evaluation
    return {
        "model": final_model,
        "train_idx": list(range(n_samples)),
        "test_idx": evaluated.tolist(),
        "metrics": metrics,
        "feature_names": list(sample_set.feature_names),
        "hyperparameters": params,
        "seed": seed,
        "target_names": target_names,
        "class_mapping": metrics["class_mapping"],
        "evaluation": evaluation,
        "oof": {
            "index": evaluated.tolist(),
            "predicted": [target_names[int(p)] for p in pooled_pred],
            "probabilities": oof_probabilities,
        },
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
