import hashlib
import json
import logging

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.analytics.services.features import (
    FEATURE_ORDERS,
    FEATURE_SCHEMA_VERSION,
)

from ..models import ModelRegistry, TrainingJob
from .data_loader import build_samples, resolve_datasets
from .trainer import STRATEGY_NAMES, serialize_model, train_and_evaluate

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
    evaluation = result["evaluation"]
    is_lopo = evaluation["strategy"] == STRATEGY_NAMES["lopo"]
    oof_by_index = {}
    if result.get("oof"):
        oof = result["oof"]
        for position, sample_index in enumerate(oof["index"]):
            oof_by_index[sample_index] = {
                "predicted": oof["predicted"][position],
                "probabilities": oof["probabilities"][position],
            }
    sample_rows = []
    for index, metadata in enumerate(sample_set.sample_metadata):
        row = dict(metadata)
        if is_lopo:
            row["split"] = (
                "lopo_evaluated" if index in test_indices else "lopo_unevaluated"
            )
            if index in oof_by_index:
                row["out_of_fold"] = oof_by_index[index]
        else:
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
        "manifest_version": 2,
        "job_id": job.pk,
        "created_at": timezone.now().isoformat(),
        "dataset_ids": [dataset.pk for dataset in datasets],
        "datasets": [
            {"id": dataset.pk, "name": dataset.name, "purpose": dataset.purpose}
            for dataset in datasets
        ],
        "view_angle": view_angle,
        "prediction_target": prediction_target,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "model_version": sample_set.model_version,
        "selected_features": list(sample_set.feature_names),
        "algorithm": job.algorithm,
        "hyperparameters": result["hyperparameters"],
        "random_seed": seed,
        "test_size": None if is_lopo else test_size,
        "split_strategy": evaluation["strategy"],
        "evaluation": evaluation,
        "sample_count": len(sample_set),
        "train_sample_ids": [
            sample_set.sample_ids[index] for index in result["train_idx"]
        ],
        "test_sample_ids": [
            sample_set.sample_ids[index] for index in result["test_idx"]
        ],
        "samples": sample_rows,
        "label_snapshot": sorted(
            [
                [
                    row["sample_id"],
                    int(bool(row["is_correct"])),
                    row.get("label_source", ""),
                ]
                for row in sample_set.sample_metadata
            ]
        ),
        "label_source_counts": {
            source: sum(
                row.get("label_source", "") == source
                for row in sample_set.sample_metadata
            )
            for source in sorted(
                {row.get("label_source", "") for row in sample_set.sample_metadata}
            )
        },
        "class_mapping": result["class_mapping"],
        "target_names": result["target_names"],
        "metrics": result["metrics"],
        "feature_warnings": list(sample_set.warnings),
        "exclusion_counts": dict(sample_set.exclusion_counts),
        "pipeline_config_hashes": dict(sample_set.pipeline_config_hashes),
        "frame_timing": "derived_from_landmark_timestamps",
        "data_warnings": list(sample_set.errors[:250]),
        "data_warning_count": len(sample_set.errors),
    }
    canonical_manifest = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    manifest["label_snapshot_sha256"] = hashlib.sha256(
        json.dumps(
            manifest["label_snapshot"], separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
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
    model_version: str | None = None,
    evaluation: str = "lopo",
    allow_mixed_pipeline: bool = False,
) -> TrainingJob:
    job.status = TrainingJob.Status.RUNNING
    job.started_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "error_message"])

    try:
        target_ids = dataset_ids or list(job.datasets.values_list("id", flat=True))
        datasets = resolve_datasets(target_ids)
        if model_version is None and not feature_selection:
            model_version = "M1"
        selected_features = feature_selection or list(FEATURE_ORDERS[model_version])
        prediction_target = (
            prediction_target
            or job.prediction_target
            or TrainingJob.PredictionTarget.BINARY_FORM
        )

        sample_set = build_samples(
            datasets=datasets,
            selected_features=selected_features,
            view_angle=view_angle or job.view_angle or None,
            prediction_target=prediction_target,
            model_version=model_version,
            allow_mixed_pipeline=allow_mixed_pipeline,
        )
        view_angle = sample_set.view_angle

        result = train_and_evaluate(
            sample_set=sample_set,
            hyperparameters=hyperparameters or {},
            test_size=test_size,
            seed=seed,
            evaluation=evaluation,
        )
        serialized_model = serialize_model(result["model"])
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
        job.feature_schema_version = FEATURE_SCHEMA_VERSION
        job.test_size = test_size
        job.random_seed = seed
        job.split_strategy = result["evaluation"]["strategy"]
        job.model_artifact.save(
            f"training_jobs/job_{job.pk}_model.json",
            ContentFile(serialized_model),
            save=False,
        )
        job.sample_count = len(sample_set)
        job.train_count = len(result["train_idx"])
        job.test_count = len(result["test_idx"])
        job.feature_selection = list(sample_set.feature_names)
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
    parser.add_argument("--model-version", choices=["M0", "M1"])
    parser.add_argument("--evaluation", choices=["lopo", "holdout"], default="lopo")
    parser.add_argument("--allow-mixed-pipeline", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--view-angle", choices=["diagonal", "frontal", "sagittal"])
    parser.add_argument(
        "--prediction-target",
        choices=["binary_form", "error_type"],
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
            model_version=args.model_version,
            evaluation=args.evaluation,
            allow_mixed_pipeline=args.allow_mixed_pipeline,
        )
    except TrainingJob.DoesNotExist:
        print(
            f"Error: TrainingJob with ID {args.job_id} does not exist.", file=sys.stderr
        )
        sys.exit(1)
