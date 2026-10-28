import logging
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.analytics.services.features import FEATURE_ORDER
from ..models import TrainingJob, ModelRegistry
from .data_loader import build_samples, group_split, resolve_datasets
from .trainer import load_model, serialize_model, train_and_evaluate

logger = logging.getLogger(__name__)

def _next_version(model_name: str) -> str:
    last_entry = (
        ModelRegistry.objects.filter(name=model_name)
        .order_by("-created_at")
        .first()
    )
    if not last_entry:
        return "1.0"

    try:
        major, minor = map(int, last_entry.version.split("."))
        return f"{major}.{minor + 1}"
    except(ValueError, AttributeError):
        return "1.0"

def run_training_job(
        job: TrainingJob,
        dataset_ids: list[int] | None = None,
        feature_selection: list[str] | None = None,
        hyperparameters: dict | None = None,
        test_size: float = 0.3,
        seed: int = 42,
        register_model: bool=True,
        model_name: str = "vectofit-squat-classifier",
) -> TrainingJob:
    job.status = TrainingJob.Status.RUNNING
    job.started_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "error_message"])

    try:
        target_ids = dataset_ids or list(
            job.datasets.values_list("id", flat=True)
        )
        
        datasets = resolve_datasets(target_ids)
        job.datasets.set(datasets)

        selected_features = feature_selection or list(FEATURE_ORDER)

        sample_set = build_samples(
            datasets=datasets, 
            selected_features=selected_features,
        )

        result = train_and_evaluate(
            sample_set=sample_set,
            hyperparameters=hyperparameters or {},
            test_size=test_size,
            seed=seed,
        )

        serialized_model = serialize_model(result["model"])

        job.model_artifact.save(
            f"training_jobs/job_{job.pk}_model.json",
            ContentFile(serialized_model),
            save=False,
        )

        job.sample_count = len(sample_set)
        job.train_count = len(result["train_idx"])
        job.test_count = len(result["test_idx"])
        job.feature_selection = selected_features
        job.hyperparameters = result["hyperparameters"]
        job.metrics = result["metrics"]
        job.status = TrainingJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.save()

        if register_model:
            version = _next_version(model_name)

            registry_entry = ModelRegistry.objects.create(
                name=model_name,
                version=version,
                training_job=job,
                algorithm=TrainingJob.Algorithm.XGBOOST,
                metrics=result["metrics"]
            )

            registry_entry.artifact.save(
                f"{model_name}_v{version}.json",
                ContentFile(serialized_model),
                save=True,
            )

        logger.info("TrainingJob %s completed successfully.", job.pk)
        return job

    except Exception as exc:
        logger.exception("TrainingJob %s failed with error: %s", job.pk, exc)

        job.status = TrainingJob.Status.FAILED
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.metrics = {}
        job.save(update_fields=["status", "error_message", "completed_at", "metrics"])

        return job

if __name__ == "__main__":
    import argparse
    import json
    import os
    import sys
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    parser = argparse.ArgumentParser(description="Run VectoFit Training Job CLI")
    parser.add_argument("--job-id", type=int, required=True)
    parser.add_argument("--dataset-ids", nargs="+", type=int)
    parser.add_argument("--features", nargs="*")
    parser.add_argument("--hyperparameters", type=str, default="{}")
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    try:
        training_job = TrainingJob.objects.get(pk=args.job_id)
        hparams = json.loads(args.hyperparameters)

        run_training_job(
            job=training_job,
            dataset_ids=args.dataset_ids,
            feature_selection=args.features,
            hyperparameters=hparams,
            test_size=args.test_size,
            seed=args.seed,
        )
    except TrainingJob.DoesNotExist:
        print(f"Error: TrainingJob with ID {args.job_id} does not exist.", file=sys.stderr)
        sys.exit(1)