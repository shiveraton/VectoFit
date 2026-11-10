import hashlib
import json
import logging

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.analytics.services.feature_schemas import schema_for_target

from ..models import ModelRegistry, TrainingJob
from .data_loader import build_samples, resolve_datasets
from .trainer import serialize_model, train_and_evaluate, training_environment

logger = logging.getLogger(__name__)


def _next_version(model_name: str) -> str:
    last_entry = (
        ModelRegistry.objects.filter(name=model_name).order_by("-created_at").first()
    )
    if not last_entry:
        return "1.0"
    try:
        major, minor = map(int, last_entry.version.split("."))
        return f"{major}.{minor + 1}"
    except (ValueError, AttributeError):
        return "1.0"


def _register_model(job, model_name, serialized_model, metrics):
    """Create a uniquely versioned registry row; retry if concurrent jobs race."""
    for attempt in range(5):
        try:
            with transaction.atomic():
                list(
                    ModelRegistry.objects.select_for_update()
                    .filter(name=model_name)
                    .values_list("id", flat=True)
                )
                version = _next_version(model_name)
                entry = ModelRegistry.objects.create(
                    name=model_name,
                    version=version,
                    training_job=job,
                    algorithm=job.algorithm,
                    metrics=metrics,
                )
                entry.artifact.save(
                    f"{model_name}_v{version}.json",
                    ContentFile(serialized_model),
                    save=True,
                )
                return entry
        except IntegrityError:
            if attempt == 4:
                raise
    raise RuntimeError("Could not allocate a unique model registry version.")


def _build_manifest(
    job, datasets, sample_set, result, view_angle, prediction_target, test_size, seed
):
    train_indices = set(result["train_idx"])
    test_indices = set(result["test_idx"])
    sample_rows = []
    for index, metadata in enumerate(sample_set.sample_metadata):
        row = dict(metadata)
        row["split"] = (
            "train"
            if index in train_indices
            else "test"
            if index in test_indices
            else "unassigned"
        )
        row["features"] = {
            feature_name: float(value)
            for feature_name, value in zip(
                sample_set.feature_names, sample_set.rows[index]
            )
        }
        sample_rows.append(row)

    manifest = {
        "manifest_version": 1,
        "environment": training_environment(),
        "job_id": job.pk,
        "created_at": timezone.now().isoformat(),
        "dataset_ids": [dataset.pk for dataset in datasets],
        "datasets": [
            {"id": dataset.pk, "name": dataset.name, "purpose": dataset.purpose}
            for dataset in datasets
        ],
        "view_angle": view_angle,
        "prediction_target": prediction_target,
        "feature_schema_version": job.feature_schema_version,
        "selected_features": list(sample_set.feature_names),
        "algorithm": job.algorithm,
        "hyperparameters": result["hyperparameters"],
        "random_seed": seed,
        "test_size": test_size,
        "split_strategy": "group_by_participant",
        "sample_count": len(sample_set),
        "train_sample_ids": [
            sample_set.sample_ids[index] for index in result["train_idx"]
        ],
        "test_sample_ids": [
            sample_set.sample_ids[index] for index in result["test_idx"]
        ],
        "samples": sample_rows,
        "class_mapping": result["class_mapping"],
        "target_names": result["target_names"],
        "metrics": result["metrics"],
        "feature_warnings": list(sample_set.warnings),
        "data_warnings": list(sample_set.errors[:250]),
        "data_warning_count": len(sample_set.errors),
        "timing_source_counts": {
            source: sum(
                1 for sample in sample_set.sample_metadata
                if sample.get("timing_source") == source
            )
            for source in sorted(
                {sample.get("timing_source") for sample in sample_set.sample_metadata}
                - {None}
            )
        },
    }
    if prediction_target == "knee_alignment":
        manifest.update({
            "eligibility_policy_version": sample_set.eligibility_policy_version,
            "exclusions": sample_set.exclusions,
            "eligibility_summary": sample_set.readiness_report(),
            "annotation_evidence": sample_set.annotation_evidence,
        })
    canonical_manifest = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    manifest["manifest_sha256"] = hashlib.sha256(canonical_manifest).hexdigest()
    return manifest


def run_training_job(
    job: TrainingJob,
    dataset_ids: list[int] | None = None,
    feature_selection: list[str] | None = None,
    hyperparameters: dict | None = None,
    test_size: float = 0.3,
    seed: int = 42,
    register_model: bool = True,
    model_name: str = "vectofit-squat-classifier",
    view_angle: str | None = None,
    prediction_target: str | None = None,
) -> TrainingJob:
    job.status = TrainingJob.Status.RUNNING
    job.started_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "error_message"])

    try:
        target_ids = dataset_ids or list(job.datasets.values_list("id", flat=True))
        datasets = resolve_datasets(target_ids)
        prediction_target = (
            prediction_target
            or job.prediction_target
            or TrainingJob.PredictionTarget.BINARY_FORM
        )
        schema = schema_for_target(prediction_target)
        selected_features = feature_selection or list(schema.feature_order)
        if prediction_target == TrainingJob.PredictionTarget.KNEE_ALIGNMENT:
            if set(selected_features) != set(schema.feature_order):
                raise ValueError("Registered M1 training requires all six FPPA features.")
            selected_features = list(schema.feature_order)

        sample_set = build_samples(
            datasets=datasets,
            selected_features=selected_features,
            view_angle=view_angle or job.view_angle or None,
            prediction_target=prediction_target,
        )
        view_angle = sample_set.view_angle

        result = train_and_evaluate(
            sample_set=sample_set,
            hyperparameters=hyperparameters or {},
            test_size=test_size,
            seed=seed,
        )
        serialized_model = serialize_model(result["model"])
        job.feature_schema_version = schema.version
        manifest = _build_manifest(
            job,
            datasets,
            sample_set,
            result,
            view_angle,
            prediction_target,
            test_size,
            seed,
        )

        job.datasets.set(datasets)
        job.view_angle = view_angle
        job.prediction_target = prediction_target
        job.test_size = test_size
        job.random_seed = seed
        job.split_strategy = "group_by_participant"
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
        job.feature_warnings = list(sample_set.warnings)
        job.training_manifest = manifest
        if register_model:
            _register_model(job, model_name, serialized_model, result["metrics"])

        job.status = TrainingJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.save()

        logger.info("TrainingJob %s completed successfully.", job.pk)
        return job

    except Exception as exc:
        logger.exception("TrainingJob %s failed with error: %s", job.pk, exc)

        for registry_entry in ModelRegistry.objects.filter(training_job=job):
            if registry_entry.artifact:
                registry_entry.artifact.delete(save=False)
        ModelRegistry.objects.filter(training_job=job).delete()
        if job.model_artifact:
            job.model_artifact.delete(save=False)

        job.status = TrainingJob.Status.FAILED
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.sample_count = 0
        job.train_count = 0
        job.test_count = 0
        job.metrics = {}
        job.feature_warnings = []
        job.training_manifest = {}
        job.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
                "sample_count",
                "train_count",
                "test_count",
                "metrics",
                "feature_warnings",
                "training_manifest",
                "model_artifact",
            ]
        )
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
    parser.add_argument("--view-angle", choices=["diagonal", "frontal", "sagittal"])
    parser.add_argument(
        "--prediction-target",
        choices=["binary_form", "error_type", "knee_alignment"],
        default="binary_form",
    )
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
            view_angle=args.view_angle,
            prediction_target=args.prediction_target,
        )
    except TrainingJob.DoesNotExist:
        print(
            f"Error: TrainingJob with ID {args.job_id} does not exist.", file=sys.stderr
        )
        sys.exit(1)
