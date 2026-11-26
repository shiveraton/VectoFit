import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, recall_score


def classification_metrics(labels, predictions):
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "balanced_accuracy": float(recall_score(
            labels, predictions, labels=np.unique(labels), average="macro", zero_division=0
        )),
        "macro_f1": float(f1_score(labels, predictions, labels=[0, 1], average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
    }


def choose_threshold(scores, labels):
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    if not len(scores) or not np.all(np.isfinite(scores)) or set(labels) != {0, 1}:
        raise ValueError("Threshold fitting requires finite scores and both training classes.")
    candidates = np.concatenate(([np.nextafter(scores.min(), -np.inf)], np.unique(scores)))
    best_threshold, best_score = None, -1.0
    for threshold in candidates:
        predictions = (scores <= threshold).astype(int)
        score = balanced_accuracy_score(labels, predictions)
        if score > best_score:
            best_threshold, best_score = float(threshold), float(score)
    return best_threshold


def evaluate_baselines(sample_set, folds):
    names = sample_set.feature_names
    columns = [names.index(name) for name in ("fppa_l_peak", "fppa_r_peak")]
    scores = np.abs(np.asarray(sample_set.rows, dtype=float)[:, columns]).max(axis=1)
    labels = np.asarray([{"bad": 0, "good": 1}[label] for label in sample_set.labels])
    majority_predictions = np.full(len(labels), -1, dtype=int)
    rule_predictions = np.full(len(labels), -1, dtype=int)
    fold_results = []
    for fold in folds:
        train = np.asarray(fold["train_idx"], dtype=int)
        test = np.asarray(fold["test_idx"], dtype=int)
        threshold = choose_threshold(scores[train], labels[train])
        majority = int(np.bincount(labels[train], minlength=2).argmax())
        majority_predictions[test] = majority
        rule_predictions[test] = (scores[test] <= threshold).astype(int)
        fold_results.append({
            "participant": fold["participant"],
            "threshold_degrees": threshold,
            "majority_class": ["bad", "good"][majority],
            "test_count": int(len(test)),
            "majority": classification_metrics(labels[test], majority_predictions[test]),
            "fppa_rule": classification_metrics(labels[test], rule_predictions[test]),
        })
    evaluated = np.flatnonzero(rule_predictions >= 0)
    return {
        "class_mapping": {"0": "bad", "1": "good"},
        "rule": "bad if max(abs(fppa_l_peak), abs(fppa_r_peak)) > threshold; otherwise good",
        "threshold_objective": "training-fold balanced_accuracy; lowest threshold wins ties",
        "dataset_majority_accuracy": float(np.bincount(labels).max() / len(labels)),
        "majority": classification_metrics(labels[evaluated], majority_predictions[evaluated]),
        "fppa_rule": classification_metrics(labels[evaluated], rule_predictions[evaluated]),
        "folds": fold_results,
        "predictions": [
            {"sample_id": sample_set.sample_ids[i], "label": int(labels[i]),
             "majority": int(majority_predictions[i]), "fppa_rule": int(rule_predictions[i])}
            for i in evaluated
        ],
    }
