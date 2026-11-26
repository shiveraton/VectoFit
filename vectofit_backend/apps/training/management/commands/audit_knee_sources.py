import json
from collections import Counter
from pathlib import Path

import numpy as np
from django.core.management.base import BaseCommand

from apps.datasets.models import DatasetVideo
from apps.training.services.data_loader import prepare_knee_samples, resolve_datasets
from apps.training.services.source_evaluation import evaluate_splits, magnitude_features
from apps.training.services.trainer import resolve_hyperparameters, training_environment


class Command(BaseCommand):
    help = "Audit FPPA distributions, source-specific evaluation, and source video coverage."

    def add_arguments(self, parser):
        parser.add_argument("--dataset-id", type=int, required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--cache")

    def handle(self, *args, **options):
        cache = Path(options["cache"]) if options["cache"] else None
        if cache and cache.exists():
            data = json.loads(cache.read_text())
            if data["dataset_id"] != options["dataset_id"]:
                raise ValueError("Cached dataset ID does not match.")
        else:
            samples = prepare_knee_samples(resolve_datasets([options["dataset_id"]]))
            videos = list(DatasetVideo.objects.filter(dataset_id=options["dataset_id"]).order_by("source_path").values(
                "id", "source_path", "participant_id", "status", "requires_manual_review", "view_angle__angle_variant"
            ))
            data = {
                "dataset_id": options["dataset_id"], "feature_names": samples.feature_names,
                "rows": samples.rows, "labels": samples.labels, "groups": samples.groups,
                "sample_ids": samples.sample_ids, "metadata": samples.sample_metadata,
                "readiness": samples.readiness_report(), "videos": videos,
            }
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        X = np.asarray(data["rows"], dtype=float)
        if (data.get("normalization") or {}).get("valid_for_comparison") is False:
            raise ValueError("This cached transformation was rejected; use the original feature snapshot.")
        y = np.asarray([{"bad": 0, "good": 1}[v] for v in data["labels"]])
        groups = np.asarray(data["groups"])
        sources = np.asarray([Path(m["source_path"]).name.split("_")[0].lower() for m in data["metadata"]])
        magnitudes = magnitude_features(X, data["feature_names"])
        distributions = []
        for source in sorted(set(sources)):
            for label, encoded in (("good", 1), ("bad", 0)):
                values = magnitudes[(sources == source) & (y == encoded), 0]
                distributions.append({
                    "source": str(source), "label": label, "count": len(values),
                    "mean": float(values.mean()), "std": float(values.std(ddof=1)),
                    **dict(zip(("min", "p10", "p50", "p90", "max"), np.quantile(values, [0, .1, .5, .9, 1]).tolist())),
                })
        def lopo(indices):
            return [
                (str(group), indices[groups[indices] != group], indices[groups[indices] == group])
                for group in sorted(set(groups[indices]))
            ]
        all_indices = np.arange(len(y))
        experiments = {"pooled_lopo": lopo(all_indices)}
        for source in sorted(set(sources)):
            indices = np.flatnonzero(sources == source)
            experiments[f"{source}_lopo"] = lopo(indices)
            others = np.flatnonzero(sources != source)
            experiments[f"{source}_to_other"] = [(f"train_{source}", indices, others)]
        params = resolve_hyperparameters(prediction_target="knee_alignment")
        report = {
            "dataset_id": options["dataset_id"], "feature_names": data["feature_names"],
            "normalization": data.get("normalization"),
            "magnitude_feature_names": ["max_abs_peak", "max_abs_bottom", "asym_bottom", "asym_peak"],
            "class_mapping": {"0": "bad", "1": "good"},
            "environment": training_environment(), "hyperparameters": params,
            "monotone_constraints": [-1, -1, 0, 0],
            "threshold_selection": "Training-fold balanced accuracy only; lowest threshold wins ties",
            "distributions": distributions, "experiments": {},
            "videos": data["videos"], "readiness": data["readiness"],
        }
        for name, folds in experiments.items():
            result = evaluate_splits(X, y, groups, sources, data["feature_names"], folds, params)
            for prediction in result["predictions"]:
                prediction["sample_id"] = data["sample_ids"][prediction["index"]]
            report["experiments"][name] = result
            self.stdout.write(f"{name}: " + json.dumps(result["models"]))
        eligible_by_video = Counter(m["dataset_video_id"] for m in data["metadata"])
        for video in report["videos"]:
            video["eligible_count"] = eligible_by_video[video["id"]]
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        self.stdout.write("max_abs_peak distributions: " + json.dumps(distributions))
        self.stdout.write(f"Wrote source diagnostic to {output}")
