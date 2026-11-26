import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from .knee_baselines import choose_threshold, classification_metrics
from .trainer import scale_pos_weight


def magnitude_features(rows, feature_names):
    rows = np.asarray(rows, dtype=float)
    def maximum(left, right):
        return np.abs(rows[:, [feature_names.index(left), feature_names.index(right)]]).max(axis=1)
    return np.column_stack([
        maximum("fppa_l_peak", "fppa_r_peak"),
        maximum("fppa_l_bottom", "fppa_r_bottom"),
        np.abs(rows[:, feature_names.index("asym_bottom")]),
        np.abs(rows[:, feature_names.index("asym_peak")]),
    ])


def metrics(labels, predictions):
    result = classification_metrics(labels, predictions)
    bad = labels == 0
    result["bad_recall"] = float(np.mean(predictions[bad] == 0)) if bad.any() else None
    result["n"] = len(labels)
    result["bad_count"] = int(bad.sum())
    return result


def evaluate_splits(rows, labels, groups, sources, feature_names, folds, params):
    X = np.asarray(rows, dtype=float)
    y = np.asarray(labels, dtype=int)
    groups, sources = np.asarray(groups), np.asarray(sources)
    magnitudes = magnitude_features(X, feature_names)
    names = ("majority", "fppa_rule", "xgboost", "magnitude_monotone_xgboost", "magnitude_logistic")
    predictions = {name: np.full(len(y), -1, dtype=int) for name in names}
    fold_results = []
    for name, train, test in folds:
        train, test = np.asarray(train, dtype=int), np.asarray(test, dtype=int)
        if set(groups[train]) & set(groups[test]):
            raise ValueError("Participant leakage between training and testing.")
        if set(y[train]) != {0, 1}:
            raise ValueError(f"Fold {name} lacks a training class.")
        threshold = choose_threshold(magnitudes[train, 0], y[train])
        predictions["majority"][test] = np.bincount(y[train], minlength=2).argmax()
        predictions["fppa_rule"][test] = (magnitudes[test, 0] <= threshold).astype(int)
        model = XGBClassifier(**params, scale_pos_weight=scale_pos_weight(y[train]))
        model.fit(X[train], y[train])
        predictions["xgboost"][test] = model.predict(X[test])
        monotone = XGBClassifier(
            **params, scale_pos_weight=scale_pos_weight(y[train]),
            monotone_constraints=(-1, -1, 0, 0),
        )
        monotone.fit(magnitudes[train], y[train])
        predictions["magnitude_monotone_xgboost"][test] = monotone.predict(magnitudes[test])
        logistic = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000))
        logistic.fit(magnitudes[train], y[train])
        predictions["magnitude_logistic"][test] = logistic.predict(magnitudes[test])
        fold_results.append({
            "fold": name, "threshold_degrees": threshold,
            "train_participants": sorted(set(groups[train].tolist())),
            "test_participants": sorted(set(groups[test].tolist())),
            "models": {model_name: metrics(y[test], pred[test]) for model_name, pred in predictions.items()},
        })
    evaluated = predictions["fppa_rule"] >= 0
    if not evaluated.any():
        raise ValueError("No held-out predictions.")
    by_source = {}
    for source in sorted(set(sources[evaluated])):
        mask = evaluated & (sources == source)
        by_source[str(source)] = {name: metrics(y[mask], pred[mask]) for name, pred in predictions.items()}
    return {
        "models": {name: metrics(y[evaluated], pred[evaluated]) for name, pred in predictions.items()},
        "by_source": by_source, "folds": fold_results,
        "predictions": [
            {"index": int(i), "label": int(y[i]), "source": str(sources[i]),
             **{name: int(pred[i]) for name, pred in predictions.items()}}
            for i in np.flatnonzero(evaluated)
        ],
    }
