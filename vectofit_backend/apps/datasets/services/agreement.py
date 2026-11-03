from collections import Counter
from itertools import combinations

from apps.datasets.models import DatasetSample

from .annotation import derive_target_label


def _kappa(observed, expected):
    if observed is None or expected is None or expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def agreement_for_dataset(dataset):
    samples = DatasetSample.objects.filter(dataset=dataset).prefetch_related(
        "knee_annotations"
    )
    fields = {
        "target_label": lambda annotation: derive_target_label(annotation),
        "left.grade": lambda annotation: annotation.get("left", {}).get("grade"),
        "right.grade": lambda annotation: annotation.get("right", {}).get("grade"),
    }
    output = {}
    for field, getter in fields.items():
        matrix = {}
        annotator_counts = Counter()
        for sample in samples:
            values = {}
            for row in sample.knee_annotations.all():
                if row.annotator_id is not None:
                    value = getter(row.annotation)
                    if value is not None:
                        values[str(row.annotator_id)] = value
                        annotator_counts[str(row.annotator_id)] += 1
            if values:
                matrix[sample.pk] = values
        multi = {sid: vals for sid, vals in matrix.items() if len(vals) >= 2}
        pair_matches, pair_total = 0, 0
        pair_scores = []
        for left, right in combinations(sorted(annotator_counts), 2):
            shared = [
                (vals[left], vals[right])
                for vals in matrix.values()
                if left in vals and right in vals
            ]
            if not shared:
                continue
            observed = sum(a == b for a, b in shared) / len(shared)
            categories = set(v for pair in shared for v in pair)
            pa = {c: sum(a == c for a, _ in shared) / len(shared) for c in categories}
            pb = {c: sum(b == c for _, b in shared) / len(shared) for c in categories}
            pair_scores.append(_kappa(observed, sum(pa[c] * pb[c] for c in categories)))
            pair_matches += sum(a == b for a, b in shared)
            pair_total += len(shared)
        rater_counts = Counter(len(v) for v in multi.values())
        n = (
            max(rater_counts, key=lambda x: (rater_counts[x], x))
            if rater_counts
            else None
        )
        fleiss_subjects = [v for v in multi.values() if len(v) == n] if n else []
        categories = {value for vals in fleiss_subjects for value in vals.values()}
        fleiss = None
        if len(fleiss_subjects) >= 2 and len(categories) > 1:
            ps, observed_terms = [], []
            for vals in fleiss_subjects:
                counts = Counter(vals.values())
                ps.append({c: counts[c] / n for c in categories})
                observed_terms.append(
                    sum(counts[c] * (counts[c] - 1) for c in categories) / (n * (n - 1))
                )
            pbar = {c: sum(p[c] for p in ps) / len(ps) for c in categories}
            fleiss = _kappa(
                sum(observed_terms) / len(observed_terms),
                sum(p * p for p in pbar.values()),
            )
        output[field] = {
            "annotators": [
                {"annotator_id": key, "count": count}
                for key, count in sorted(annotator_counts.items())
            ],
            "multi_annotated_samples": len(multi),
            "observed_agreement": pair_matches / pair_total if pair_total else None,
            "pairwise_cohen_kappa": (
                sum(score for score in pair_scores if score is not None)
                / sum(score is not None for score in pair_scores)
                if any(score is not None for score in pair_scores)
                else None
            ),
            "fleiss_kappa": fleiss,
            "fleiss_raters": n,
            "fleiss_excluded_samples": sum(
                bool(values) and len(values) != n for values in matrix.values()
            ),
        }
    return output
