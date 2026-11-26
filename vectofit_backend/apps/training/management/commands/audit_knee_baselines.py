import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.training.models import TrainingJob
from apps.training.services.data_loader import prepare_knee_samples, resolve_datasets
from apps.training.services.knee_baselines import evaluate_baselines
from apps.training.services.trainer import train_and_evaluate


class Command(BaseCommand):
    help = "Compare majority, training-fold FPPA thresholds, and XGBoost on identical participant folds."

    def add_arguments(self, parser):
        parser.add_argument("--dataset-ids", nargs="+", type=int, required=True)
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        samples = prepare_knee_samples(resolve_datasets(options["dataset_ids"]))
        result = train_and_evaluate(samples, split_strategy=TrainingJob.TrainingSplit.LOPO)
        report = evaluate_baselines(samples, result["folds"])
        report.update({
            "dataset_ids": options["dataset_ids"],
            "evaluation_method": "leave_one_participant_out",
            "eligible_count": len(samples),
            "class_counts": samples.class_distribution,
            "feature_names": samples.feature_names,
            "hyperparameters": result["hyperparameters"],
            "xgboost": result["metrics"],
        })
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        for name in ("majority", "fppa_rule", "xgboost"):
            metrics = report[name]
            self.stdout.write(
                f"{name}: accuracy={metrics['accuracy']:.4f} "
                f"balanced_accuracy={metrics['balanced_accuracy']:.4f} "
                f"macro_f1={metrics['macro_f1']:.4f}"
            )
        self.stdout.write(f"Wrote baseline audit to {output}")
