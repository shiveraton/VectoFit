from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.datasets.models import Dataset
from django.shortcuts import get_object_or_404

from .models import ModelRegistry, TrainingJob
from .serializers import (
    ModelRegistrySerializer,
    ModelStateSerializer,
    TrainingJobRequestSerializer,
    TrainingJobSerializer,
)
from .services import run_training_job

class TrainingJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TrainingJob.objects.prefetch_related("datasets").all()
    serializer_class = TrainingJobSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get("status")

        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        return queryset

class TrainingJobCreateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = (TrainingJobRequestSerializer(data=request.data))
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        job = TrainingJob.objects.create(
            algorithm=data["algorithm"],
            feature_selection=data["feature_selection"],
            hyperparameters=data["hyperparameters"],
            random_seed=data["random_seed"],
        )
        job.datasets.set(Dataset.objects.filter(pk__in=data["dataset_ids"]))

        run_training_job(
            job,
            dataset_ids=data["dataset_ids"],
            feature_selection=data["feature_selection"],
            hyperparameters=data["hyperparameters"],
            test_size=data["test_size"],
            seed=data["random_seed"],
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
    permission_classes = [permissions.IsAdminUser]

class ModelStateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        model = get_object_or_404(
            (
                ModelRegistry.objects.select_related("training_job").prefetch_related("training_job__datasets")
            ),
            pk=pk
        )

        serializer = ModelStateSerializer(
            model,
            context={"request": request}
        )

        return Response(serializer.data)