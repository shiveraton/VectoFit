import json
from pathlib import Path
from typing import ClassVar

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from xgboost.core import XGBoostError

from apps.analytics.services.features import FEATURE_SCHEMA_VERSION
from apps.datasets.models import Dataset, Participant
from apps.training.services.data_loader import (
    TrainingConfigurationError,
    resolve_datasets,
)
from apps.training.services.evaluation import readiness_report
from apps.training.services.model_inference import (
    ModelInferenceError,
    predict_with_active_model,
)
from apps.training.services.run_training_job import run_training_job
from apps.training.services.trainer import load_model

from .models import ModelRegistry, TrainingJob
from .serializers import (
    ModelPredictionRequestSerializer,
    ModelRegistrySerializer,
    ModelStateSerializer,
    TrainingJobRequestSerializer,
    TrainingJobSerializer,
)


class TrainingJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TrainingJob.objects.prefetch_related("datasets").all()
    serializer_class = TrainingJobSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        return queryset


class TrainingJobCreateView(APIView):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def post(self, request):
        serializer = TrainingJobRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        feature_selection = data["feature_selection"]
        split_strategy = (
            "leave_one_participant_out"
            if data["evaluation"] == "lopo"
            else "group_by_participant"
        )

        job = TrainingJob.objects.create(
            algorithm=data["algorithm"],
            view_angle=data["view_angle"],
            prediction_target=data["prediction_target"],
            feature_selection=feature_selection,
            hyperparameters=data["hyperparameters"],
            random_seed=data["random_seed"],
            test_size=data["test_size"],
            split_strategy=split_strategy,
        )
        job.datasets.set(Dataset.objects.filter(pk__in=data["dataset_ids"]))
        run_training_job(
            job,
            dataset_ids=data["dataset_ids"],
            feature_selection=feature_selection,
            hyperparameters=data["hyperparameters"],
            test_size=data["test_size"],
            seed=data["random_seed"],
            view_angle=data["view_angle"],
            prediction_target=data["prediction_target"],
            model_version=data["model_version"],
            evaluation=data["evaluation"],
        )
        job.refresh_from_db()

        if job.status == TrainingJob.Status.FAILED:
            return Response(
                TrainingJobSerializer(job, context={"request": request}).data,
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            TrainingJobSerializer(job, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ModelRegistryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModelRegistry.objects.select_related("training_job").all()
    serializer_class = ModelRegistrySerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        registry_entry = self.get_object()
        job = registry_entry.training_job
        if job.view_angle not in {"diagonal", "frontal", "sagittal"}:
            return Response(
                {
                    "detail": "This legacy model has no recorded camera angle. Retrain it with an explicit angle before activation."
                },
                status=409,
            )
        if job.feature_schema_version != FEATURE_SCHEMA_VERSION:
            return Response(
                {
                    "detail": "This model was trained with an unsupported feature schema. Retrain it with the current schema before activation.",
                    "expected": FEATURE_SCHEMA_VERSION,
                    "received": job.feature_schema_version,
                },
                status=409,
            )
        if job.status != TrainingJob.Status.COMPLETED:
            return Response(
                {
                    "detail": "Only models from completed training jobs can be activated."
                },
                status=409,
            )
        if not registry_entry.artifact:
            return Response(
                {"detail": "The registry model has no artifact file."}, status=409
            )
        try:
            with registry_entry.artifact.open("rb") as model_file:
                artifact_bytes = model_file.read()
        except (OSError, ValueError) as exc:
            return Response(
                {"detail": f"The registered artifact cannot be read: {exc}"}, status=409
            )
        if not artifact_bytes:
            return Response(
                {"detail": "The registered model artifact is empty."}, status=409
            )
        try:
            load_model(artifact_bytes)
        except (OSError, ValueError, AttributeError, XGBoostError) as exc:
            return Response(
                {
                    "detail": f"The registered artifact is not a valid XGBoost model: {exc}"
                },
                status=409,
            )

        with transaction.atomic():
            ModelRegistry.objects.select_for_update().filter(
                name=registry_entry.name,
                training_job__view_angle=job.view_angle,
                training_job__prediction_target=job.prediction_target,
                is_active=True,
            ).exclude(pk=registry_entry.pk).update(is_active=False)
            registry_entry.is_active = True
            registry_entry.save(update_fields=["is_active"])

        return Response(
            ModelRegistrySerializer(registry_entry, context={"request": request}).data
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="predict",
        permission_classes=[permissions.IsAuthenticated],
    )
    def predict(self, request):
        serializer = ModelPredictionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = predict_with_active_model(
                model_name=data["model_name"],
                view_angle=data["view_angle"],
                prediction_target=data["prediction_target"],
                feature_schema_version=data["feature_schema_version"],
                features=data["features"],
            )
        except ModelInferenceError as exc:
            return Response(exc.payload, status=exc.status_code)

        return Response(result)


class ModelStateView(APIView):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get(self, request, pk):
        model = get_object_or_404(
            ModelRegistry.objects.select_related("training_job").prefetch_related(
                "training_job__datasets"
            ),
            pk=pk,
        )
        serializer = ModelStateSerializer(model, context={"request": request})
        return Response(serializer.data)


class ExperimentReadinessView(APIView):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get(self, request):
        ids = [
            int(part)
            for part in request.query_params.get("dataset_ids", "").split(",")
            if part.strip().isdigit()
        ]
        if not ids:
            return Response(
                {"detail": "dataset_ids is required (comma-separated)."}, status=400
            )
        view_angle = request.query_params.get("view_angle", "frontal")
        try:
            report = readiness_report(resolve_datasets(ids), view_angle)
        except TrainingConfigurationError as exc:
            return Response({"detail": str(exc)}, status=400)

        counts = report.get("per_participant_class_counts", {})
        pks = [int(group.split("-", 1)[1]) for group in counts]
        codes = dict(
            Participant.objects.filter(pk__in=pks).values_list("pk", "participant_code")
        )
        origin = report.get("per_participant_label_origin", {})
        participants = [
            {
                "group": group,
                "code": codes.get(int(group.split("-", 1)[1]), group),
                "good": class_counts.get("1", 0),
                "bad": class_counts.get("0", 0),
                "human_labelled": origin.get(group, {}).get("human", 0),
            }
            for group, class_counts in counts.items()
        ]
        participants.sort(key=lambda row: row["code"])
        lopo = report.get("lopo", {"viable": False})
        return Response(
            {
                "ok": report["ok"],
                "reason": report.get("reason", ""),
                "view_angle": view_angle,
                "n_reps": report.get("samples", 0),
                "mixed_pipeline": report.get("mixed_pipeline", False),
                "pipeline_hash_count": len(report.get("pipeline_config_hashes", {})),
                "exclusion_counts": report.get("exclusion_counts", {}),
                "lopo": {
                    "viable": lopo.get("viable", False),
                    "folds": lopo.get("folds", 0),
                    "reason": lopo.get("reason", ""),
                },
                "participants": participants,
            }
        )


EXPERIMENT_BUNDLES = {"main": "", "demo": "demo"}


def _experiments_dir() -> Path:
    default = Path(settings.BASE_DIR).parent / "research" / "experiments"
    return Path(getattr(settings, "EXPERIMENTS_DIR", default))


def _participant_pk(group: str):
    prefix, _, tail = group.partition("participant-")
    return int(tail) if prefix == "" and tail.isdigit() else None


class ExperimentResultsView(APIView):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get(self, request):
        bundle = request.query_params.get("bundle", "main")
        if bundle not in EXPERIMENT_BUNDLES:
            return Response({"detail": "Unknown bundle."}, status=400)
        base = _experiments_dir() / EXPERIMENT_BUNDLES[bundle]
        results_path, provenance_path = (
            base / "experiment_results.json",
            base / "provenance.json",
        )
        if not results_path.is_file():
            return Response({"available": False, "bundle": bundle})

        results = json.loads(results_path.read_text(encoding="utf-8"))
        provenance = (
            json.loads(provenance_path.read_text(encoding="utf-8"))
            if provenance_path.is_file()
            else None
        )
        groups = list(results.get("participants", {}))
        codes = {}
        if not results.get("demo"):
            pks = [pk for pk in map(_participant_pk, groups) if pk is not None]
            codes = {
                f"participant-{pk}": code
                for pk, code in Participant.objects.filter(pk__in=pks).values_list(
                    "pk", "participant_code"
                )
            }
        return Response(
            {
                "available": True,
                "bundle": bundle,
                "results": results,
                "provenance": provenance,
                "participant_codes": {g: codes.get(g, g) for g in groups},
            }
        )
