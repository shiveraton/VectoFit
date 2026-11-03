from collections import Counter, defaultdict

import numpy as np
from scipy.stats import binomtest, wilcoxon

from .data_loader import (
    DatasetNotUsableError,
    InsufficientGroupsError,
    TrainingConfigurationError,
    build_samples,
    leave_one_participant_out_folds,
)
from .trainer import InsufficientDataError, train_and_evaluate


def build_paired_sample_sets(
    datasets, view_angle, prediction_target="binary_form", **build_kwargs
):
    m0 = build_samples(
        datasets,
        None,
        view_angle=view_angle,
        prediction_target=prediction_target,
        model_version="M0",
        **build_kwargs,
    )
    m1 = build_samples(
        datasets,
        None,
        view_angle=view_angle,
        prediction_target=prediction_target,
        model_version="M1",
        **build_kwargs,
    )
    return m0, m1


def readiness_report(
    datasets, view_angle, prediction_target="binary_form", model_version="M1"
):
    report = {
        "ok": False,
        "view_angle": view_angle,
        "prediction_target": prediction_target,
        "model_version": model_version,
    }
    try:
        sample_set = build_samples(
            datasets,
            None,
            view_angle=view_angle,
            prediction_target=prediction_target,
            model_version=model_version,
            allow_mixed_pipeline=True,
        )
    except (DatasetNotUsableError, TrainingConfigurationError) as exc:
        report["reason"] = str(exc)
        return report

    per_participant = defaultdict(Counter)
    for group, label in zip(sample_set.groups, sample_set.labels):
        per_participant[group][str(label)] += 1
    label_origin = defaultdict(Counter)
    for group, meta in zip(sample_set.groups, sample_set.sample_metadata):
        label_origin[group][meta.get("label_origin", "unknown")] += 1
    report.update(
        features=list(sample_set.feature_names),
        samples=len(sample_set),
        participants=len(per_participant),
        class_distribution=sample_set.class_distribution,
        per_participant_class_counts={
            group: dict(counts) for group, counts in sorted(per_participant.items())
        },
        per_participant_label_origin={
            group: dict(counts) for group, counts in sorted(label_origin.items())
        },
        exclusion_counts=dict(sample_set.exclusion_counts),
        pipeline_config_hashes=dict(sample_set.pipeline_config_hashes),
        mixed_pipeline=len(sample_set.pipeline_config_hashes) > 1,
    )
    try:
        folds, skipped = leave_one_participant_out_folds(
            sample_set.groups, list(sample_set.labels)
        )
        report["lopo"] = {"viable": True, "folds": len(folds), "skipped": skipped}
    except InsufficientGroupsError as exc:
        report["lopo"] = {"viable": False, "reason": str(exc)}
    report["ok"] = report["lopo"]["viable"] and not report["mixed_pipeline"]
    return report


def format_readiness_report(report):
    lines = [
        f"READINESS ({report['model_version']}, {report['view_angle']}, ",
        f"{report['prediction_target']}): {'READY' if report['ok'] else 'NOT READY'}",
    ]
    if "reason" in report:
        lines.append(f"  reason: {report['reason']}")
        return "\n".join(lines)
    lines.append(
        f"  usable reps: {report['samples']} from {report['participants']} participants"
    )
    lines.append(f"  classes: {report['class_distribution']}")
    lines.append(f"  excluded by reason: {report['exclusion_counts'] or 'none'}")
    hashes = ", ".join(
        f"{(digest[:12] or '(none)')}={count}"
        for digest, count in sorted(report["pipeline_config_hashes"].items())
    )
    lines.append(
        f"  pipeline hashes: {hashes}"
        + ("  <-- MIXED, training will refuse" if report["mixed_pipeline"] else "")
    )
    lopo = report["lopo"]
    if lopo["viable"]:
        lines.append(
            f"  LOPO: {lopo['folds']} folds, {len(lopo['skipped'])} skipped participants"
        )
    else:
        lines.append(f"  LOPO not viable: {lopo['reason']}")
    return "\n".join(lines)


def _balanced_accuracy(y_true, y_pred):
    recalls = []
    for label in np.unique(y_true):
        mask = y_true == label
        recalls.append(float(np.mean(y_pred[mask] == label)))
    return float(np.mean(recalls))


def _encode(sample_set, target_names):
    if sample_set.prediction_target == "binary_form":
        return np.asarray([int(label) for label in sample_set.labels], dtype=int)
    index = {name: i for i, name in enumerate(target_names)}
    return np.asarray([index[str(label)] for label in sample_set.labels], dtype=int)


def _assert_paired(first, second):
    same = (
        list(first.sample_ids) == list(second.sample_ids)
        and list(first.groups) == list(second.groups)
        and list(first.labels) == list(second.labels)
        and first.prediction_target == second.prediction_target
    )
    if not same:
        raise ValueError(
            "The two sample sets are not paired: sample ids, participant groups, "
            "labels and prediction target must be identical."
        )


def paired_model_comparison(
    sample_set_a,
    sample_set_b,
    hyperparameters=None,
    seed=42,
    n_bootstrap=2000,
    bootstrap_seed=0,
):
    _assert_paired(sample_set_a, sample_set_b)
    result_a = train_and_evaluate(
        sample_set_a, hyperparameters, seed=seed, evaluation="lopo"
    )
    result_b = train_and_evaluate(
        sample_set_b, hyperparameters, seed=seed, evaluation="lopo"
    )
    if result_a["oof"]["index"] != result_b["oof"]["index"]:
        raise InsufficientDataError(
            "The two models were evaluated on different samples, so they cannot "
            "be compared pairwise."
        )

    target_names = result_a["target_names"]
    n_classes = len(target_names)
    index = np.asarray(result_a["oof"]["index"], dtype=int)
    y_all = _encode(sample_set_a, target_names)
    y_true = y_all[index]
    groups = np.asarray(sample_set_a.groups)[index]

    def predictions(result):
        lookup = {name: i for i, name in enumerate(target_names)}
        return np.asarray([lookup[name] for name in result["oof"]["predicted"]])

    pred_a, pred_b = predictions(result_a), predictions(result_b)
    correct_a, correct_b = pred_a == y_true, pred_b == y_true

    def summary(result, pred):
        return {
            "features": list(result["feature_names"]),
            "accuracy": float(np.mean(pred == y_true)),
            "balanced_accuracy": _balanced_accuracy(y_true, pred),
            "roc_auc": result["metrics"].get("roc_auc"),
        }

    a, b = summary(result_a, pred_a), summary(result_b, pred_b)
    delta = {
        "accuracy": b["accuracy"] - a["accuracy"],
        "balanced_accuracy": b["balanced_accuracy"] - a["balanced_accuracy"],
    }

    rng = np.random.default_rng(bootstrap_seed)
    unique_groups = np.unique(groups)
    members = {group: np.flatnonzero(groups == group) for group in unique_groups}
    draws_acc, draws_bal = [], []
    for _ in range(n_bootstrap):
        chosen = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        pick = np.concatenate([members[group] for group in chosen])
        yt = y_true[pick]
        if len(np.unique(yt)) < n_classes:
            continue
        draws_acc.append(
            float(np.mean(pred_b[pick] == yt) - np.mean(pred_a[pick] == yt))
        )
        draws_bal.append(
            _balanced_accuracy(yt, pred_b[pick]) - _balanced_accuracy(yt, pred_a[pick])
        )

    def interval(draws):
        if not draws:
            return None
        low, high = np.percentile(draws, [2.5, 97.5])
        return [float(low), float(high)]

    bootstrap = {
        "method": "participant_cluster_bootstrap",
        "n_requested": int(n_bootstrap),
        "n_used": len(draws_acc),
        "accuracy_delta_ci95": interval(draws_acc),
        "balanced_accuracy_delta_ci95": interval(draws_bal),
    }

    only_a = int(np.sum(correct_a & ~correct_b))
    only_b = int(np.sum(~correct_a & correct_b))
    discordant = only_a + only_b
    mcnemar = {
        "a_correct_b_wrong": only_a,
        "a_wrong_b_correct": only_b,
        "p_value_exact": float(binomtest(min(only_a, only_b), discordant, 0.5).pvalue)
        if discordant
        else 1.0,
        "note": "Repetitions are clustered within participants; descriptive only.",
    }

    per_participant = []
    for group in unique_groups:
        mask = members[group]
        acc_a = float(np.mean(correct_a[mask]))
        acc_b = float(np.mean(correct_b[mask]))
        per_participant.append(
            {
                "participant": str(group),
                "n_reps": len(mask),
                "accuracy_a": acc_a,
                "accuracy_b": acc_b,
                "delta": acc_b - acc_a,
            }
        )
    deltas = np.asarray([row["delta"] for row in per_participant])
    wilcoxon_p = None
    if np.count_nonzero(deltas) >= 6:
        wilcoxon_p = float(wilcoxon(deltas, zero_method="wilcox").pvalue)

    return {
        "n_samples": len(index),
        "n_participants": len(unique_groups),
        "a": a,
        "b": b,
        "delta": delta,
        "bootstrap": bootstrap,
        "mcnemar": mcnemar,
        "per_participant": per_participant,
        "participant_wilcoxon_p": wilcoxon_p,
        "results": {"a": result_a, "b": result_b},
    }
