import logging
from typing import ClassVar

from django.db import transaction
from django.http import FileResponse, HttpResponseNotFound
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .inference_serializers import (
    InferenceHistorySerializer,
    InferenceRunRequestSerializer,
    InferenceRunSerializer,
    InferenceSimulationSerializer,
    InferenceUploadSerializer,
)
from .models import InferenceRun, InferenceSimulation, InferenceStatus
from .services.inference_simulation import model_snapshot

logger = logging.getLogger(__name__)
ACTIVE_STATUSES = [InferenceStatus.PENDING, InferenceStatus.PROCESSING]


def enqueue_inference(run_id):
    from .tasks import run_inference_task

    try:
        run_inference_task.delay(run_id)
    except Exception:
        logger.exception("Could not queue inference run=%s", run_id)
        run = InferenceRun.objects.get(pk=run_id)
        message = "Could not queue inference. Try again."
        InferenceRun.objects.filter(pk=run_id, status=InferenceStatus.PENDING).update(
            status=InferenceStatus.FAILED,
            error_message=message,
            completed_at=timezone.now(),
        )
        InferenceSimulation.objects.filter(
            pk=run.simulation_id, status=InferenceStatus.PENDING
        ).update(
            status=InferenceStatus.FAILED,
            error_message=message,
            completed_at=timezone.now(),
        )


def deny_public_inference_video(request, path):
    return HttpResponseNotFound()


class InferenceHistoryPagination(PageNumberPagination):
    page_size = 10


class InferenceSimulationViewSet(viewsets.GenericViewSet):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]
    parser_classes: ClassVar[list] = [MultiPartParser, FormParser, JSONParser]
    pagination_class = InferenceHistoryPagination
    serializer_class = InferenceSimulationSerializer

    def get_queryset(self):
        return InferenceSimulation.objects.filter(
            creator=self.request.user
        ).prefetch_related("runs")

    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(
            InferenceHistorySerializer(page, many=True).data
        )

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    def create(self, request):
        serializer = InferenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = serializer.validated_data["video_file"]
        model = serializer.validated_data["model_id"]
        with transaction.atomic():
            simulation = InferenceSimulation.objects.create(
                creator=request.user,
                video_file=video,
                original_filename=video.name,
            )
            run = InferenceRun.objects.create(
                simulation=simulation,
                model=model,
                model_snapshot=model_snapshot(model),
            )
            transaction.on_commit(lambda: enqueue_inference(run.pk))
        return Response(
            self.get_serializer(simulation).data, status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=["post"])
    def runs(self, request, pk=None):
        serializer = InferenceRunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        model = serializer.validated_data["model_id"]
        with transaction.atomic():
            simulation = (
                self.get_queryset().select_for_update().get(pk=self.get_object().pk)
            )
            run = simulation.runs.filter(model=model).first()
            if run and run.status in [*ACTIVE_STATUSES, InferenceStatus.COMPLETED]:
                return Response(InferenceRunSerializer(run).data)
            if simulation.runs.filter(status__in=ACTIVE_STATUSES).exists():
                return Response(
                    {"detail": "Wait for the current model to finish."}, status=409
                )
            if run is None:
                run = InferenceRun(simulation=simulation, model=model)
            run.status = InferenceStatus.PENDING
            run.error_message = ""
            run.predictions = []
            run.model_loading_ms = None
            run.inference_ms = None
            run.completed_at = None
            run.model_snapshot = model_snapshot(model)
            run.save()
            transaction.on_commit(lambda: enqueue_inference(run.pk))
        return Response(
            InferenceRunSerializer(run).data, status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=["get"])
    def video(self, request, pk=None):
        simulation = self.get_object()
        try:
            video = simulation.video_file.open("rb")
        except (OSError, ValueError):
            return Response({"detail": "The saved video is unavailable."}, status=404)
        response = FileResponse(video, filename=simulation.original_filename)
        response["Cache-Control"] = "private, no-store"
        return response

    def destroy(self, request, pk=None):
        with transaction.atomic():
            simulation = (
                self.get_queryset().select_for_update().get(pk=self.get_object().pk)
            )
            if simulation.runs.filter(status__in=ACTIVE_STATUSES).exists():
                return Response(
                    {"detail": "Wait for processing to finish before deleting."},
                    status=409,
                )
            try:
                simulation.video_file.delete(save=False)
            except OSError:
                logger.exception("Could not delete inference video=%s", simulation.pk)
                return Response(
                    {"detail": "Could not delete the video. Try again."}, status=503
                )
            simulation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
