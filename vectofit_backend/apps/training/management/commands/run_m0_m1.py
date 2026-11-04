import json
from pathlib import Path

import numpy as np
from django.core.management.base import BaseCommand, CommandError

from apps.analytics.services.fppa import (
    FEATURE_SCHEMA_VERSION,
    M0_FEATURES,
    M1_FEATURES,
    extract_fppa_features,
)
from apps.datasets.models import Dataset, DatasetVideo
from apps.datasets.services.knee_label import final_knee_target
from apps.training.services.trainer import lopo_evaluate
from apps.training.services.data_loader import SampleSet

VALGUS_CUTOFF_DEG = 10.0
VARUS_CUTOFF_DEG = 10.0
SENSITIVITY_CUTOFFS_DEG = (5.0, 15.0)
BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 42


# Evaluate the fixed signed-peak FPPA threshold rule.
def threshold_rule_baseline(records, cutoff):
    labels = []
    predictions = []
    groups = []
    for record in records:
        labels.append({"bad": 0, "good": 1}[record["target"]])
        peak_values = (record["fppa_l_peak"], record["fppa_r_peak"])
        is_bad = any(
            value > cutoff or value < -cutoff for value in peak_values
        )
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


# Return binary macro-F1 and confusion-matrix metrics.
def _classification_metrics(labels, predictions):
    from sklearn.metrics import confusion_matrix, f1_score

    return {
        "macro_f1": float(
            f1_score(labels, predictions, labels=[0, 1], average="macro", zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
    }


# Estimate a paired participant bootstrap interval for the M1-M0 delta.
def bootstrap_delta_interval(m0, m1):
    m0_scores = {row["participant"]: row["macro_f1"] for row in m0["per_participant"]}
    m1_scores = {row["participant"]: row["macro_f1"] for row in m1["per_participant"]}
    deltas = np.asarray([m1_scores[key] - m0_scores[key] for key in m0_scores])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples = [
        float(np.mean(rng.choice(deltas, size=len(deltas), replace=True)))
        for _ in range(BOOTSTRAP_ITERATIONS)
    ]
    return {
        "lower": float(np.percentile(samples, 2.5)),
        "upper": float(np.percentile(samples, 97.5)),
        "iterations": BOOTSTRAP_ITERATIONS,
        "seed": BOOTSTRAP_SEED,
    }


def _load_records(dataset_ids, frame_width, frame_height, native_fps):
    samples = Dataset.objects.filter(pk__in=dataset_ids).prefetch_related(
        "samples__rep_assessment",
        "samples__dataset_video__participant",
        "samples__dataset_video__view_angle",
    )
    records = []
    for dataset in samples:
        for sample in dataset.samples.filter(
            dataset_video__view_angle__angle_variant="frontal",
            dataset_video__status=DatasetVideo.Status.READY,
        ):
            target = final_knee_target(sample)
            if target not in {"good", "bad"}:
                continue
            features, metadata = extract_fppa_features(
                sample.rep_assessment.landmark_series,
                frame_width=frame_width,
                frame_height=frame_height,
                native_fps=native_fps,
            )
            if not metadata["valid"]:
                continue
            records.append(
                {
                    "sample_id": sample.pk,
                    "participant": sample.dataset_video.participant.participant_code,
                    "target": target,
                    **features,
                }
            )
    return records


class Command(BaseCommand):
    help = "Run exploratory pilot LOPO comparisons for FPPA M0 and M1."

    def add_arguments(self, parser):
        parser.add_argument("--dataset-ids", nargs="+", type=int, required=True)
        parser.add_argument("--output", default="m0_m1_results.json")
        parser.add_argument("--frame-width", type=int, default=1920)
        parser.add_argument("--frame-height", type=int, default=1080)
        parser.add_argument("--fps", type=float, default=30.0)

    def handle(self, *args, **options):
        records = _load_records(
            options["dataset_ids"],
            options["frame_width"],
            options["frame_height"],
            options["fps"],
        )
        if not records:
            raise CommandError("No eligible frontal FPPA repetitions were found.")

        results = {
            "label": "exploratory pilot",
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "M0_features": list(M0_FEATURES),
            "M1_features": list(M1_FEATURES),
        }
        for name, features in (("M0", M0_FEATURES), ("M1", M1_FEATURES)):
            sample_set = SampleSet(
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
            results[name] = lopo_evaluate(sample_set)

        results["delta_macro_f1"] = results["M1"]["macro_f1"] - results["M0"]["macro_f1"]
        results["delta_macro_f1_bootstrap_95"] = bootstrap_delta_interval(
            results["M0"], results["M1"]
        )
        results["threshold_rule_baseline"] = {
            "rule": "bad if either knee peak filtered signed FPPA exceeds the valgus or varus cutoff",
            "primary": {
                "label": "primary_predeclared",
                **threshold_rule_baseline(records, VALGUS_CUTOFF_DEG),
            },
            "sensitivity": [
                {
                    "label": "sensitivity",
                    **threshold_rule_baseline(records, cutoff),
                }
                for cutoff in SENSITIVITY_CUTOFFS_DEG
            ],
        }
        Path(options["output"]).write_text(json.dumps(results, indent=2), encoding="utf-8")
        self.stdout.write(f"Wrote exploratory pilot results to {options['output']}")
