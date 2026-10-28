from collections.abc import Iterable, Mapping, Sequence
from math import ceil, isfinite
from typing import Any

FINDINGS_REGISTRY: dict[tuple[str, str], dict[str, str]] = {
    ("knee_angle", "insufficient_depth"): {
        "code": "INSUFFICIENT_DEPTH",
        "title": "Insufficient squat depth",
        "summary": (
            "The measured minimum knee angle exceeded the configured "
            "depth threshold in these repetitions."
        ),
        "cue": ("Aim to reach the configured depth target while maintaining control."),
        "threshold_key": "knee_depth",
        "metric_key": "depth_deg",
    },
    ("trunk_angle", "excessive_trunk_lean"): {
        "code": "EXCESSIVE_TRUNK_LEAN",
        "title": "Excessive trunk lean",
        "summary": (
            "Peak trunk lean exceeded the configured limit in these repetitions."
        ),
        "cue": (
            "Brace your trunk and maintain a controlled torso angle "
            "during descent and ascent."
        ),
        "threshold_key": "trunk_lean",
        "metric_key": "trunk_lean_deg",
    },
    ("asymmetry", "excessive"): {
        "code": "EXCESSIVE_ASYMMETRY",
        "title": "Excessive bilateral asymmetry",
        "summary": (
            "Left-right knee-angle asymmetry exceeded the configured "
            "limit in these repetitions."
        ),
        "cue": (
            "Use a stable camera position and repeat the movement with both knees "
            "clearly visible; compare their knee-angle path across the repetition."
        ),
        "threshold_key": "asymmetry",
        "metric_key": "asymmetry_pct",
    },
}

_METRIC_DEFINITIONS: tuple[dict[str, str], ...] = (
    {
        "key": "depth_deg",
        "label": "Minimum knee angle",
        "unit": "°",
        "threshold_key": "knee_depth",
    },
    {
        "key": "trunk_lean_deg",
        "label": "Maximum trunk lean",
        "unit": "°",
        "threshold_key": "trunk_lean",
    },
    {
        "key": "asymmetry_pct",
        "label": "Bilateral asymmetry",
        "unit": "%",
        "threshold_key": "asymmetry",
    },
)

_COVERAGE_LABELS = {
    "rom": "Range of motion",
    "hip_angle": "Hip angle",
    "velocity": "Movement velocity",
    "knee_angle": "Knee angle",
    "trunk_angle": "Trunk lean",
    "asymmetry": "Bilateral asymmetry",
}


def _mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping or an empty mapping for malformed data."""
    return value if isinstance(value, Mapping) else {}


def _field(value: Any, name: str, default: Any = None) -> Any:
    """Read a field from a model instance or dictionary."""
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _number(value: Any) -> float | None:
    """Return a finite number, excluding booleans and invalid values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    result = float(value)
    return result if isfinite(result) else None


def _compact_rep(rep: Any, fallback_n: int) -> dict[str, Any]:
    """Extract the three report metrics and recognized finding flags."""
    analysis = _mapping(_field(rep, "analysis_result"))
    metrics = _mapping(analysis.get("metrics"))
    classifications = _mapping(analysis.get("classifications"))

    stored_number = _number(_field(rep, "rep_number"))
    n = int(stored_number) if stored_number is not None else fallback_n

    knee_result = _mapping(classifications.get("knee_angle"))
    knee_evaluation = _mapping(knee_result.get("evaluation"))

    depth = _number(metrics.get("knee_angle"))
    if depth is None:
        depth = _number(knee_evaluation.get("measured_minimum_knee_angle_deg"))

    trunk_values = metrics.get("trunk_angle")
    trunk_samples: list[float] = []

    if isinstance(trunk_values, (list, tuple)):
        trunk_samples = [
            abs(value) for item in trunk_values if (value := _number(item)) is not None
        ]
    elif (trunk_value := _number(trunk_values)) is not None:
        trunk_samples = [abs(trunk_value)]

    trunk_lean = max(trunk_samples) if trunk_samples else None

    if trunk_lean is None:
        trunk_evaluation = _mapping(
            _mapping(classifications.get("trunk_angle")).get("evaluation")
        )
        trunk_lean = _number(trunk_evaluation.get("maximum_measured_lean_deg"))

    asymmetry = _number(metrics.get("asymmetry"))
    if asymmetry is None:
        asymmetry_evaluation = _mapping(
            _mapping(classifications.get("asymmetry")).get("evaluation")
        )
        asymmetry = _number(asymmetry_evaluation.get("measured_asymmetry"))

    flags = [
        definition["code"]
        for (
            metric_key,
            expected_classification,
        ), definition in FINDINGS_REGISTRY.items()
        if _mapping(classifications.get(metric_key)).get("classification")
        == expected_classification
    ]

    return {
        "n": n,
        "depth_deg": depth,
        "trunk_lean_deg": trunk_lean,
        "asymmetry_pct": asymmetry,
        "flags": flags,
    }


def _metric_rows(
    reps: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Aggregate available metrics without losing each metric's worst rep."""
    rows: list[dict[str, Any]] = []

    for definition in _METRIC_DEFINITIONS:
        target = _number(thresholds.get(definition["threshold_key"]))
        if target is None:
            continue

        values = [
            (int(rep["n"]), value)
            for rep in reps
            if (value := _number(rep.get(definition["key"]))) is not None
        ]

        if not values:
            continue

        worst_rep, worst_value = max(values, key=lambda item: item[1])

        rows.append(
            {
                "key": definition["key"],
                "label": definition["label"],
                "unit": definition["unit"],
                "target": target,
                "mean": sum(value for _, value in values) / len(values),
                "worst": {
                    "rep": worst_rep,
                    "value": worst_value,
                },
                "passed_reps": sum(1 for _, value in values if value <= target),
            }
        )

    return rows


def _pattern(
    affected_reps: Sequence[int],
    total_reps: int,
) -> str:
    """Classify the temporal distribution of a finding."""
    affected = sorted(set(affected_reps))

    if total_reps > 0 and len(affected) / total_reps >= 0.80:
        return "constant"

    if len(affected) < 2:
        return "isolated"

    back_half_count = sum(1 for rep_number in affected if rep_number > total_reps / 2)
    back_half_ratio = back_half_count / len(affected)

    if back_half_ratio >= 0.75:
        return "worsening"

    if back_half_ratio <= 0.25:
        return "improving"

    return "isolated"


def _trends(
    reps: Sequence[Mapping[str, Any]],
) -> dict[str, float | None]:
    """Calculate depth drift and leave invalid velocity-loss claims unset."""
    depth_drift: float | None = None

    if len(reps) >= 3:
        third_size = ceil(len(reps) / 3)

        first_values = [
            value
            for rep in reps[:third_size]
            if (value := _number(rep.get("depth_deg"))) is not None
        ]
        last_values = [
            value
            for rep in reps[-third_size:]
            if (value := _number(rep.get("depth_deg"))) is not None
        ]

        if first_values and last_values:
            depth_drift = sum(last_values) / len(last_values) - sum(first_values) / len(
                first_values
            )

    # TODO: Estimate velocity loss only after valid per-phase velocity
    # measurements and appropriate physical units are available.
    return {
        "depth_drift_deg": depth_drift,
        "velocity_loss_pct": None,
    }


def _headline(
    findings: Sequence[Mapping[str, Any]],
    verdict_status: str,
    total_reps: int,
) -> str:
    """Generate a concise headline from the highest-priority finding."""
    if verdict_status == "clean" or not findings:
        return "No issues were flagged by the configured form checks."

    top = sorted(
        findings,
        key=lambda finding: (
            finding["severity"] == "major",
            len(finding["affected_reps"]),
        ),
        reverse=True,
    )[0]

    affected_count = len(top["affected_reps"])

    if verdict_status == "needs_work":
        return (
            f"{top['title']} needs attention; it affected "
            f"{affected_count} of {total_reps} reps."
        )

    return f"{top['title']} was detected in {affected_count} of {total_reps} reps."


def build_session_report(
    reps: Iterable[Any],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the versioned session report from saved per-rep results."""
    indexed_reps = list(enumerate(reps, start=1))

    def rep_sort_key(item: tuple[int, Any]) -> tuple[float, int]:
        index, rep = item
        number = _number(_field(rep, "rep_number"))
        return (number if number is not None else float(index), index)

    indexed_reps.sort(key=rep_sort_key)

    compact_reps: list[dict[str, Any]] = []
    prepared: list[tuple[Any, dict[str, Any], Mapping[str, Any]]] = []

    for fallback_n, (_, rep) in enumerate(indexed_reps, start=1):
        compact = _compact_rep(rep, fallback_n)
        analysis = _mapping(_field(rep, "analysis_result"))
        classifications = _mapping(analysis.get("classifications"))

        compact_reps.append(compact)
        prepared.append((rep, compact, classifications))

    total_reps = len(compact_reps)
    findings: list[dict[str, Any]] = []

    for (
        classification_key,
        expected_classification,
    ), definition in FINDINGS_REGISTRY.items():
        affected_reps: list[int] = []
        excesses: list[float] = []

        target = _number(thresholds.get(definition["threshold_key"]))

        for _, compact, classifications in prepared:
            classification_data = _mapping(classifications.get(classification_key))

            if classification_data.get("classification") != expected_classification:
                continue

            affected_reps.append(int(compact["n"]))

            evaluation = _mapping(classification_data.get("evaluation"))
            excess = _number(evaluation.get("difference"))

            if excess is None:
                measured = _number(compact.get(definition["metric_key"]))
                if measured is not None and target is not None:
                    excess = max(0.0, measured - target)

            excesses.append(max(0.0, excess or 0.0))

        if not affected_reps:
            continue

        worst_excess = max(excesses, default=0.0)
        affected_ratio = len(affected_reps) / total_reps

        relative_excess_is_major = (
            target is not None and target > 0 and worst_excess / target >= 0.25
        ) or (target == 0 and worst_excess > 0)

        severity = (
            "major" if relative_excess_is_major or affected_ratio >= 0.50 else "minor"
        )

        findings.append(
            {
                "code": definition["code"],
                "title": definition["title"],
                "summary": definition["summary"],
                "cue": definition["cue"],
                "severity": severity,
                "affected_reps": sorted(set(affected_reps)),
                "worst_excess": worst_excess,
                "pattern": _pattern(affected_reps, total_reps),
            }
        )

    findings.sort(
        key=lambda finding: (
            finding["severity"] == "major",
            len(finding["affected_reps"]),
        ),
        reverse=True,
    )

    flagged_reps = sum(1 for rep in compact_reps if rep["flags"])
    clean_reps = total_reps - flagged_reps

    if not flagged_reps:
        verdict_status = "clean"
    elif any(finding["severity"] == "major" for finding in findings):
        verdict_status = "needs_work"
    else:
        verdict_status = "minor_issues"

    coverage: list[str] = []
    seen_coverage: set[str] = set()

    for _, _, classifications in prepared:
        for key in sorted(classifications):
            classification_data = _mapping(classifications.get(key))

            if classification_data.get("classification") != "not_evaluated":
                continue

            evaluation = _mapping(classification_data.get("evaluation"))
            reason = evaluation.get("reason")
            label = _COVERAGE_LABELS.get(key, key.replace("_", " "))

            entry = f"{label}: {reason}" if reason else f"{label}: Not evaluated."

            if entry not in seen_coverage:
                seen_coverage.add(entry)
                coverage.append(entry)

    metric_rows = _metric_rows(compact_reps, thresholds)

    # TODO: Populate this only when score aggregation has been defined
    # and the hybrid classifier supplies validated per-rep scores.
    scores = None

    return {
        "schema_version": 1,
        "verdict": {
            "status": verdict_status,
            "headline": _headline(findings, verdict_status, total_reps),
            "clean_reps": clean_reps,
            "total_reps": total_reps,
        },
        "metrics": metric_rows,
        "findings": findings,
        "trends": _trends(compact_reps),
        "reps": compact_reps,
        "coverage": {
            "not_evaluated": coverage,
        },
        "scores": scores,
    }
