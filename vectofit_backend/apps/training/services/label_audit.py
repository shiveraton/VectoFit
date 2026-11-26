import math
import random
from collections import defaultdict
from itertools import combinations

from sklearn.metrics import cohen_kappa_score, confusion_matrix
from rest_framework.exceptions import ValidationError

from apps.datasets.serializers import KneeAnnotationField
from apps.datasets.services.knee_label import knee_target


def select_audit_samples(rows, per_source=20, seed=42):
    rng = random.Random(seed)
    sources = defaultdict(lambda: defaultdict(list))
    for row in rows:
        sources[row["source"]][row["participant_id"]].append(row)
    selected = []
    for source, participants in sorted(sources.items()):
        if sum(map(len, participants.values())) < per_source:
            raise ValueError(f"Source {source!r} has fewer than {per_source} eligible samples.")
        groups = list(participants.values())
        rng.shuffle(groups)
        for group in groups:
            rng.shuffle(group)
        count = 0
        while count < per_source:
            for group in groups:
                if group and count < per_source:
                    selected.append(group.pop())
                    count += 1
    return selected


def agreement(left, right):
    classes = ["good", "bad"]
    value = float(cohen_kappa_score(left, right, labels=classes))
    return {
        "n": len(left),
        "agreement": sum(a == b for a, b in zip(left, right)) / len(left),
        "kappa": value if math.isfinite(value) else None,
        "classes": classes,
        "confusion_matrix": confusion_matrix(left, right, labels=classes).tolist(),
    }


def score_label_audit(manifest, reviews):
    expected = {row["audit_id"] for row in manifest["samples"]}
    ratings = {"current": {r["audit_id"]: r["target"] for r in manifest["samples"]}}
    for name, review in reviews.items():
        rows = review["samples"]
        if len(rows) != len(expected) or {r["audit_id"] for r in rows} != expected:
            raise ValueError(f"{name}: sample IDs must match the frozen audit exactly.")
        ratings[name] = {}
        for row in rows:
            try:
                annotation = KneeAnnotationField().to_internal_value(row["annotation"])
            except ValidationError as exc:
                raise ValueError(f"{name}: invalid annotation for {row['audit_id']}: {exc}") from exc
            target = knee_target(annotation)
            if target == "incomplete":
                raise ValueError(f"{name}: incomplete annotation for {row['audit_id']}.")
            ratings[name][row["audit_id"]] = target
    results = {}
    strata = {"all": manifest["samples"]}
    for source in sorted({r["source"] for r in manifest["samples"]}):
        strata[source] = [r for r in manifest["samples"] if r["source"] == source]
    for stratum, rows in strata.items():
        results[stratum] = {}
        for left, right in combinations(ratings, 2):
            ids = [r["audit_id"] for r in rows]
            results[stratum][f"{left}_vs_{right}"] = agreement(
                [ratings[left][i] for i in ids], [ratings[right][i] for i in ids]
            )
    return results
