from typing import ClassVar

import json
import logging
from django.db import transaction
from django.conf import settings
from pathlib import Path
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services.feature_schemas import schema_for_target
from apps.datasets.models import Dataset
from apps.training.services.model_card import build_model_card
from apps.training.services.model_inference import (
    ModelInferenceError,
    predict_with_active_model,
)

from .models import ModelRegistry, TrainingJob
from .serializers import (
    ModelPredictionRequestSerializer,
    ModelRegistrySerializer,
    ModelStateSerializer,
    TrainingJobRequestSerializer,
    TrainingJobSerializer,
)

logger = logging.getLogger(__name__)


def _enqueue_training_job(job_id: int, task_kwargs: dict) -> None:
    from .tasks import run_training_job_task

    try:
        run_training_job_task.delay(job_id, **task_kwargs)
    except Exception as exc:
        logger.exception("Could not queue training job=%s", job_id)
        TrainingJob.objects.filter(pk=job_id, status=TrainingJob.Status.PENDING).update(
            status=TrainingJob.Status.FAILED,
            error_message=f"Could not queue training: {exc}",
            completed_at=timezone.now(),
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
        feature_selection = data.get("feature_selection") or list(
            schema_for_target(data["prediction_target"]).feature_order
        )

        job = TrainingJob.objects.create(
            feature_schema_version=schema_for_target(data["prediction_target"]).version,
            algorithm=data["algorithm"],
            view_angle=data["view_angle"],
            prediction_target=data["prediction_target"],
            feature_selection=feature_selection,
            hyperparameters=data["hyperparameters"],
            random_seed=data["random_seed"],
            test_size=data["test_size"],
        )
        job.datasets.set(Dataset.objects.filter(pk__in=data["dataset_ids"]))
        task_kwargs = {
            "dataset_ids": data["dataset_ids"],
            "feature_selection": feature_selection,
            "hyperparameters": data["hyperparameters"],
            "test_size": data["test_size"],
            "seed": data["random_seed"],
            "view_angle": data["view_angle"],
            "prediction_target": data["prediction_target"],
        }
        transaction.on_commit(
            lambda job_id=job.pk, kwargs=task_kwargs: _enqueue_training_job(
                job_id, kwargs
            )
        )
        job.refresh_from_db()
        return Response(
            TrainingJobSerializer(job, context={"request": request}).data,
            status=status.HTTP_202_ACCEPTED,
        )


class ModelRegistryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModelRegistry.objects.select_related("training_job").all()
    serializer_class = ModelRegistrySerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        registry_entry = self.get_object()
        job = registry_entry.training_job
        model_card = build_model_card(registry_entry)
        if not model_card["activation"]["allowed"]:
            blockers = model_card["activation"]["blockers"]
            payload = {
                "detail": (
                    blockers[0]["detail"]
                    if blockers
                    else "This model does not satisfy the activation readiness checks."
                ),
                "blockers": blockers,
                "model_card": model_card,
            }
            failed_codes = {blocker["code"] for blocker in blockers}
            if "feature_schema" in failed_codes:
                from apps.analytics.services.feature_schemas import CURRENT

                payload["expected"] = CURRENT.get(job.prediction_target)
                payload["received"] = job.feature_schema_version
            return Response(payload, status=409)

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


class PilotResultsView(APIView):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get(self, request):
        path = Path(settings.PILOT_RESULTS_PATH)
        if not path.is_file():
            return Response({"detail": "No pilot results have been generated."}, status=404)
        try:
            results = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return Response({"detail": f"Pilot results cannot be read: {exc}"}, status=500)
        return Response(results)
