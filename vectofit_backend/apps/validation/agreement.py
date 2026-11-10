from collections import Counter
from rest_framework.exceptions import ValidationError

from apps.datasets.services.knee_label import knee_label_evidence
from apps.datasets.serializers import KneeAnnotationField


def consensus_labels(sample):
    evidence = knee_label_evidence(sample)
    records = [row for row in evidence["annotations"] if row["annotation"] is not None]
    if not records:
        return dict.fromkeys(("left_knee", "right_knee", "overall"), "missing")
    for row in records:
        if row["annotator_id"] is None:
            return dict.fromkeys(("left_knee", "right_knee", "overall"), "missing_human_provenance")
        try:
            KneeAnnotationField().to_internal_value(row["annotation"])
        except ValidationError:
            return dict.fromkeys(("left_knee", "right_knee", "overall"), "incomplete")
    result = {"overall": evidence["target"] or "missing"}
    for side in ("left", "right"):
        grades = {row["annotation"][side]["grade"] for row in records}
        result[f"{side}_knee"] = next(iter(grades)) if len(grades) == 1 else "disputed"
    return result


def agreement_metrics(pairs):
    count = len(pairs)
    matches = sum(left == right for left, right in pairs)
    if not count:
        return {"paired_count": 0, "agreement_count": 0, "agreement_percent": "",
                "cohens_kappa": "", "kappa_status": "no_pairs"}
    first = Counter(left for left, _ in pairs)
    second = Counter(right for _, right in pairs)
    expected = sum(first[label] * second[label] for label in first) / count ** 2
    observed = matches / count
    return {"paired_count": count, "agreement_count": matches,
            "agreement_percent": round(observed * 100, 6),
            "cohens_kappa": round((observed - expected) / (1 - expected), 6) if expected < 1 else "",
            "kappa_status": "defined" if expected < 1 else "constant_marginals"}
