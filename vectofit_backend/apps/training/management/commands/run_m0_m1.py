import hashlib
import json
from pathlib import Path

import numpy as np
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.analytics.services.fppa import (
    FEATURE_SCHEMA_VERSION,
    FPPA_CUTOFF_DEG,
    M0_FEATURES,
    M1_FEATURES,
)
from apps.training.services.data_loader import (
    SampleSet,
    build_samples,
    resolve_datasets,
)
from apps.training.services.trainer import lopo_evaluate, training_environment

SENSITIVITY_CUTOFFS_DEG = (5.0, 15.0)
BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 42


def threshold_rule_baseline(records, cutoff):
    labels = []
    predictions = []
    groups = []
    for record in records:
        labels.append({"bad": 0, "good": 1}[record["target"]])
        peak_values = (record["fppa_l_peak"], record["fppa_r_peak"])
        is_bad = any(value > cutoff or value < -cutoff for value in peak_values)
        predictions.append(0 if is_bad else 1)
        groups.append(record["participant"])

    per_participant = []
    for participant in sorted(set(groups)):
        indices = [i for i, group in enumerate(groups) if group == participant]
        participant_metrics = _classification_metrics(
            [labels[i] for i in indices],
            [predictions[i] for i in indices],
        )
        per_participant.append(
            {
                "participant": participant,
                "macro_f1": participant_metrics["macro_f1"],
                "sample_count": len(indices),
            }
        )
    metrics = _classification_metrics(labels, predictions)
    return {
        "macro_f1": metrics["macro_f1"],
        "confusion_matrix": metrics["confusion_matrix"],
        "per_participant": per_participant,
        "cutoff_degrees": {"valgus": cutoff, "varus": cutoff},
    }


def _classification_metrics(labels, predictions):
    from sklearn.metrics import confusion_matrix, f1_score

    return {
        "macro_f1": float(
            f1_score(
                labels, predictions, labels=[0, 1], average="macro", zero_division=0
            )
        ),
        "confusion_matrix": confusion_matrix(
            labels, predictions, labels=[0, 1]
        ).tolist(),
    }


def bootstrap_delta_interval(m0, m1):
    from sklearn.metrics import f1_score

    m0_rows = m0["oof_predictions"]
    m1_rows = m1["oof_predictions"]
    participants = sorted({row["participant"] for row in m0_rows})
    if [
        (row.get("sample_id"), row["participant"], row["label"]) for row in m0_rows
    ] != [(row.get("sample_id"), row["participant"], row["label"]) for row in m1_rows]:
        raise CommandError(
            "M0 and M1 LOPO outputs must use the same ordered samples and labels."
        )

    paired_rows = {participant: ([], []) for participant in participants}
    for m0_row, m1_row in zip(m0_rows, m1_rows):
        m0_group, m1_group = paired_rows[m0_row["participant"]]
        m0_group.append(m0_row)
        m1_group.append(m1_row)

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        selected = rng.choice(participants, size=len(participants), replace=True)
        m0_labels, m0_predictions, m1_labels, m1_predictions = [], [], [], []
        for participant in selected:
            m0_selected, m1_selected = paired_rows[participant]
            m0_labels.extend(row["label"] for row in m0_selected)
            m0_predictions.extend(row["prediction"] for row in m0_selected)
            m1_labels.extend(row["label"] for row in m1_selected)
            m1_predictions.extend(row["prediction"] for row in m1_selected)
        m0_score = f1_score(
            m0_labels, m0_predictions, labels=[0, 1], average="macro", zero_division=0
        )
        m1_score = f1_score(
            m1_labels, m1_predictions, labels=[0, 1], average="macro", zero_division=0
        )
        samples.append(float(m1_score - m0_score))
    return {
        "lower": float(np.percentile(samples, 2.5)),
        "upper": float(np.percentile(samples, 97.5)),
        "iterations": BOOTSTRAP_ITERATIONS,
        "seed": BOOTSTRAP_SEED,
    }


def _load_samples(dataset_ids, frame_width, frame_height):
    return build_samples(
        resolve_datasets(dataset_ids),
        list(M1_FEATURES),
        view_angle="frontal",
        prediction_target="knee_alignment",
        fallback_frame_width=frame_width,
        fallback_frame_height=frame_height,
    )


class Command(BaseCommand):
    help = "Run exploratory pilot LOPO comparisons for FPPA M0 and M1."

    def add_arguments(self, parser):
        parser.add_argument("--dataset-ids", nargs="+", type=int, required=True)
        parser.add_argument("--output", default="m0_m1_results.json")
        parser.add_argument("--frame-width", type=int, default=1280)
        parser.add_argument("--frame-height", type=int, default=720)
        parser.add_argument(
            "--fps",
            type=float,
            default=30.0,
            help="Deprecated; timing is read from sample metadata or the source video.",
        )

    def handle(self, *args, **options):
        sample_set = _load_samples(
            options["dataset_ids"], options["frame_width"], options["frame_height"]
        )
        records = [
            {
                "sample_id": sample_id,
                "participant": group,
                "target": target,
                **dict(zip(sample_set.feature_names, row)),
            }
            for sample_id, group, target, row in zip(
                sample_set.sample_ids,
                sample_set.groups,
                sample_set.labels,
                sample_set.rows,
            )
        ]

        results = {
            "label": "exploratory pilot",
            "evaluation_method": "leave_one_participant_out",
            "environment": training_environment(),
            "dataset_ids": options["dataset_ids"],
            "created_at": timezone.now().isoformat(),
            "samples": [
                {**metadata, "features": dict(zip(sample_set.feature_names, row))}
                for metadata, row in zip(sample_set.sample_metadata, sample_set.rows)
            ],
            "excluded_samples": sample_set.errors,
            "eligibility_policy_version": sample_set.eligibility_policy_version,
            "exclusions": sample_set.exclusions,
            "eligibility_summary": sample_set.readiness_report(),
            "annotation_evidence": sample_set.annotation_evidence,
            "model_definitions": {
                "M0": "XGBoost with four FPPA features",
                "M1": "XGBoost with four FPPA features and bilateral asymmetry",
                "threshold": "Separate fixed signed-peak FPPA cutoff rule",
            },
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "M0_features": list(M0_FEATURES),
            "M1_features": list(M1_FEATURES),
        }
        for name, features in (("M0", M0_FEATURES), ("M1", M1_FEATURES)):
            model_samples = SampleSet(
                rows=[[record[feature] for feature in features] for record in records],
                labels=[record["target"] for record in records],
                groups=[record["participant"] for record in records],
                features=list(features),
                feature_names=list(features),
                warnings=[],
                errors=[],
                prediction_target="knee_alignment",
                sample_ids=[record["sample_id"] for record in records],
            )
            results[name] = lopo_evaluate(model_samples)

        results["delta_macro_f1"] = (
            results["M1"]["macro_f1"] - results["M0"]["macro_f1"]
        )
        results["delta_macro_f1_bootstrap_95"] = bootstrap_delta_interval(
            results["M0"], results["M1"]
        )
        results["threshold_rule_baseline"] = {
            "rule": "bad if either knee peak filtered signed FPPA exceeds the valgus or varus cutoff",
            "primary": {
                "label": "primary_predeclared",
                **threshold_rule_baseline(records, FPPA_CUTOFF_DEG),
            },
            "sensitivity": [
                {
                    "label": "sensitivity",
                    **threshold_rule_baseline(records, cutoff),
                }
                for cutoff in SENSITIVITY_CUTOFFS_DEG
            ],
        }
        results["manifest_sha256"] = hashlib.sha256(
            json.dumps(results, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        Path(options["output"]).write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )
        self.stdout.write(f"Wrote exploratory pilot results to {options['output']}")
