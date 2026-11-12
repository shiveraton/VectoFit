"""Model-card and activation-readiness checks for registered models.

The model card is a read-only, derived view over an existing
``ModelRegistry`` row, its ``TrainingJob``, and the recorded training
manifest. It does not mutate registry state or change training semantics.
Its purpose is to make the evidence behind a model explicit before the
model is allowed to serve inference.
"""

import hashlib
import json
from collections import Counter
from typing import ClassVar

from xgboost.core import XGBoostError

from apps.analytics.services.feature_schemas import (
    CURRENT,
    schema_for_version,
)

from ..models import TrainingJob
from .trainer import load_model

MODEL_CARD_VERSION = "model_card_v1"
VALID_VIEW_ANGLES: ClassVar[frozenset] = frozenset({"diagonal", "frontal", "sagittal"})
NUMERIC_METRICS: ClassVar[tuple] = (
    "accuracy",
    "balanced_accuracy",
    "precision",
    "recall",
    "f1",
)

STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"


def _check(code, label, status, detail, remediation=None):
    return {
        "code": code,
        "label": label,
        "status": status,
        "detail": detail,
        "remediation": remediation,
    }


def _manifest_digest(manifest):
    payload = {
        key: value
        for key, value in manifest.items()
        if key not in {"manifest_sha256", "manifest_hash"}
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _extract_class_metadata(job, metrics):
    manifest = job.training_manifest if isinstance(job.training_manifest, dict) else {}
    raw_mapping = manifest.get("class_mapping") or metrics.get("class_mapping") or {}
    raw_names = manifest.get("target_names") or metrics.get("target_names") or []

    mapping = {}
    if isinstance(raw_mapping, dict):
        for key, value in raw_mapping.items():
            try:
                mapping[int(key)] = str(value)
            except (TypeError, ValueError):
                continue

    target_names = (
        [str(name) for name in raw_names] if isinstance(raw_names, list) else []
    )
    if not mapping and target_names:
        mapping = {index: name for index, name in enumerate(target_names)}
    if not target_names and mapping:
        target_names = [mapping[index] for index in sorted(mapping)]

    return mapping, target_names


def _artifact_check(entry):
    artifact = entry.artifact
    if not artifact:
        return False, False, "The registry entry has no artifact file."

    try:
        with artifact.open("rb") as model_file:
            artifact_bytes = model_file.read()
    except (OSError, ValueError) as exc:
        return True, False, f"The registered artifact cannot be read: {exc}"

    if not artifact_bytes:
        return True, False, "The registered model artifact is empty."

    try:
        load_model(artifact_bytes)
    except (OSError, ValueError, AttributeError, XGBoostError) as exc:
        return (
            True,
            False,
            f"The registered artifact is not a valid XGBoost model: {exc}",
        )

    return True, True, "The registered artifact is readable and loads as XGBoost."


def _data_provenance(manifest):
    samples = (
        manifest.get("samples") if isinstance(manifest.get("samples"), list) else []
    )
    participants = {
        str(sample.get("participant_group"))
        for sample in samples
        if sample.get("participant_group")
    }
    origins = Counter(
        str(sample.get("label_origin") or "unknown") for sample in samples
    )
    splits = Counter(str(sample.get("split") or "unknown") for sample in samples)
    return {
        "participant_count": len(participants),
        "label_origin_counts": dict(sorted(origins.items())),
        "split_counts": dict(sorted(splits.items())),
    }


def build_model_card(entry):
    job = entry.training_job
    manifest = job.training_manifest if isinstance(job.training_manifest, dict) else {}
    metrics = job.metrics or entry.metrics or {}
    if not isinstance(metrics, dict):
        metrics = {}

    class_mapping, target_names = _extract_class_metadata(job, metrics)
    checks = []

    checks.append(
        _check(
            "training_completed",
            "Training job completed",
            STATUS_PASS if job.status == TrainingJob.Status.COMPLETED else STATUS_FAIL,
            f"Training job #{job.pk} status is {job.status}.",
            None
            if job.status == TrainingJob.Status.COMPLETED
            else "Retrain the model and confirm the job reaches COMPLETED.",
        )
    )

    angle_recorded = job.view_angle in VALID_VIEW_ANGLES
    checks.append(
        _check(
            "view_angle",
            "Camera angle recorded",
            STATUS_PASS if angle_recorded else STATUS_FAIL,
            f"Recorded camera angle: {job.view_angle or 'unspecified'}.",
            None
            if angle_recorded
            else "Retrain with an explicit diagonal, frontal, or sagittal angle.",
        )
    )

    expected_schema = CURRENT.get(job.prediction_target)
    schema = schema_for_version(job.feature_schema_version)
    schema_matches = (
        schema is not None
        and schema.trainable
        and expected_schema == job.feature_schema_version
    )
    checks.append(
        _check(
            "feature_schema",
            "Feature schema compatible",
            STATUS_PASS if schema_matches else STATUS_FAIL,
            (
                f"Trained with {job.feature_schema_version or 'an unspecified schema'}; "
                f"current schema for {job.prediction_target} is "
                f"{expected_schema or 'unspecified'}."
            ),
            None
            if schema_matches
            else "Retrain with the current feature extraction schema before activation.",
        )
    )

    if job.prediction_target == TrainingJob.PredictionTarget.KNEE_ALIGNMENT:
        m1_contract_ok = (
            job.view_angle == "frontal"
            and schema is not None
            and list(job.feature_selection) == list(schema.feature_order)
        )
        checks.append(
            _check(
                "m1_contract",
                "Frontal M1 configuration",
                STATUS_PASS if m1_contract_ok else STATUS_FAIL,
                "Registered M1 models require the frontal view and six FPPA features in schema order.",
                None
                if m1_contract_ok
                else "Retrain using the frontal M1 configuration.",
            )
        )

    artifact_present, artifact_loadable, artifact_detail = _artifact_check(entry)
    checks.append(
        _check(
            "artifact_present",
            "Registry artifact present",
            STATUS_PASS if artifact_present else STATUS_FAIL,
            artifact_detail
            if not artifact_present
            else "A registry artifact file exists.",
            None if artifact_present else "Re-register or retrain the model artifact.",
        )
    )
    checks.append(
        _check(
            "artifact_loadable",
            "Artifact loads as XGBoost",
            STATUS_PASS if artifact_loadable else STATUS_FAIL,
            artifact_detail,
            None
            if artifact_loadable
            else "Replace the artifact with a valid serialized XGBoost model.",
        )
    )

    manifest_present = bool(manifest)
    checks.append(
        _check(
            "manifest_present",
            "Training manifest recorded",
            STATUS_PASS if manifest_present else STATUS_FAIL,
            (
                f"Manifest contains {len(manifest.get('samples', []))} sample records."
                if manifest_present
                else "No training manifest is stored for this model."
            ),
            None
            if manifest_present
            else "Retrain so the exact sample IDs, labels, and splits are recorded.",
        )
    )

    recorded_hash = manifest.get("manifest_sha256")
    if not manifest_present:
        integrity_status = STATUS_FAIL
        integrity_detail = "No manifest exists, so integrity cannot be verified."
    elif not recorded_hash:
        integrity_status = STATUS_WARN
        integrity_detail = (
            "The manifest has no recorded SHA-256 hash (legacy manifest)."
        )
    else:
        recomputed = _manifest_digest(manifest)
        if recomputed == recorded_hash:
            integrity_status = STATUS_PASS
            integrity_detail = "Manifest hash matches the recorded SHA-256."
        else:
            integrity_status = STATUS_FAIL
            integrity_detail = (
                "Manifest hash does not match the recorded SHA-256; the stored "
                "manifest may have been modified after training."
            )

    checks.append(
        _check(
            "manifest_integrity",
            "Manifest integrity verified",
            integrity_status,
            integrity_detail,
            None
            if integrity_status == STATUS_PASS
            else "Retrain from the original data to regenerate a verifiable manifest.",
        )
    )

    provenance = _data_provenance(manifest)
    nonhuman_count = sum(
        count
        for origin, count in provenance["label_origin_counts"].items()
        if origin != "human"
    )
    provenance_ok = provenance["participant_count"] >= 2 and nonhuman_count == 0
    checks.append(
        _check(
            "data_provenance",
            "Training labels and participants are defensible",
            STATUS_PASS if provenance_ok else STATUS_FAIL,
            (
                f"{provenance['participant_count']} participants and "
                f"{nonhuman_count} labels without verified human provenance recorded."
            ),
            None
            if provenance_ok
            else (
                "Retrain with at least two participants and explicit human "
                "annotations for every training label."
            ),
        )
    )

    class_metadata_ok = bool(class_mapping) and bool(target_names)
    expected_indices = set(range(len(target_names)))
    if class_metadata_ok:
        class_metadata_ok = expected_indices.issubset(set(class_mapping))
    checks.append(
        _check(
            "class_metadata",
            "Class labels recorded",
            STATUS_PASS if class_metadata_ok else STATUS_FAIL,
            (
                "Class order: "
                + ", ".join(
                    f"{index}={class_mapping[index]}"
                    for index in sorted(class_mapping)
                    if index in class_mapping
                )
                if class_mapping
                else "No class mapping or target names were recorded."
            ),
            None
            if class_metadata_ok
            else "Retrain so the confusion matrix has an explicit class-label ordering.",
        )
    )

    numeric_metrics = [
        name for name in NUMERIC_METRICS if _is_number(metrics.get(name))
    ]
    metrics_ok = bool(numeric_metrics) and (job.test_count or 0) > 0
    checks.append(
        _check(
            "test_metrics",
            "Held-out metrics available",
            STATUS_PASS if metrics_ok else STATUS_FAIL,
            (
                f"Recorded metrics: {', '.join(numeric_metrics)}; "
                f"test samples: {job.test_count or 0}."
                if metrics_ok
                else "Held-out metrics or a non-empty test set are missing."
            ),
            None
            if metrics_ok
            else "Complete an evaluation with at least one held-out test sample.",
        )
    )

    test_distribution = metrics.get("test_class_distribution") or {}
    if not isinstance(test_distribution, dict):
        test_distribution = {}
    missing_classes = [
        name
        for name in target_names
        if not _is_number(test_distribution.get(name))
        or test_distribution.get(name, 0) <= 0
    ]
    coverage_ok = bool(target_names) and not missing_classes
    checks.append(
        _check(
            "test_class_coverage",
            "Every class represented in the test set",
            STATUS_PASS if coverage_ok else STATUS_FAIL,
            (
                "Test class counts: "
                + ", ".join(
                    f"{name}={test_distribution.get(name, 0)}" for name in target_names
                )
                if coverage_ok
                else (
                    "Classes missing from the held-out test set: "
                    + ", ".join(missing_classes or ["unknown"])
                )
            ),
            None
            if coverage_ok
            else "Collect data from more participants so every class is held out.",
        )
    )

    split_ok = job.split_strategy in {"group_by_participant", "leave_one_participant_out"}
    checks.append(
        _check(
            "group_split",
            "Participant-grouped split",
            STATUS_PASS if split_ok else STATUS_WARN,
            f"Recorded split strategy: {job.split_strategy or 'unspecified'}.",
            None
            if split_ok
            else "Prefer a participant-grouped split to prevent subject-level leakage.",
        )
    )

    for index, warning in enumerate(job.feature_warnings or []):
        checks.append(
            _check(
                f"feature_warning_{index + 1}",
                "Feature extraction warning",
                STATUS_WARN,
                str(warning),
                "Review this caveat before interpreting model results.",
            )
        )

    blockers = [check for check in checks if check["status"] == STATUS_FAIL]
    warnings = [check for check in checks if check["status"] == STATUS_WARN]

    if blockers:
        status = "blocked"
    elif warnings:
        status = "warning"
    else:
        status = "ready"

    return {
        "schema_version": MODEL_CARD_VERSION,
        "status": status,
        "generated_from": {
            "job_id": job.pk,
            "registry_entry_id": entry.pk,
            "manifest_version": manifest.get("manifest_version"),
            "manifest_sha256": recorded_hash,
        },
        "activation": {
            "allowed": not blockers,
            "blockers": blockers,
            "warnings": warnings,
        },
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "passed_checks": sum(
                1 for check in checks if check["status"] == STATUS_PASS
            ),
            "warning_checks": len(warnings),
            "failed_checks": len(blockers),
        },
        "class_mapping": {
            str(index): name for index, name in sorted(class_mapping.items())
        },
        "target_names": target_names,
        "prediction_target": job.prediction_target,
        "view_angle": job.view_angle,
        "feature_schema_version": job.feature_schema_version,
        "evaluation_scope": "held_out_test_set",
        "held_out_test_count": job.test_count,
        "data_provenance": provenance,
    }
