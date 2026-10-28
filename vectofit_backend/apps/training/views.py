from typing import ClassVar

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from xgboost.core import XGBoostError

from apps.analytics.services.features import FEATURE_ORDER, FEATURE_SCHEMA_VERSION
from apps.datasets.models import Dataset
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
        feature_selection = data.get("feature_selection") or list(FEATURE_ORDER)

        job = TrainingJob.objects.create(
            algorithm=data["algorithm"],
            view_angle=data["view_angle"],
            prediction_target=data["prediction_target"],
            feature_selection=feature_selection,
            hyperparameters=data["hyperparameters"],
            random_seed=data["random_seed"],
            test_size=data["test_size"],
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
