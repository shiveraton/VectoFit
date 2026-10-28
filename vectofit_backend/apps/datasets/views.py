import uuid
import zipfile
import json
import logging

from datetime import timedelta
from pathlib import PurePosixPath, Path

from rest_framework import permissions, viewsets, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.response import Response

from django.utils import timezone
from django.db import transaction
from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone

from .models import Dataset, DatasetVideo, DatasetSample, Participant, ViewAngle
from .serializers import DatasetSerializer, DatasetVideoSerializer, DatasetSampleSerializer, DatasetBulkImportSerializer, ParticipantSerializer, ViewAngleSerializer
from .services.tasks import process_dataset_video_task
from .services.bulk_import import empty_manifest, inspect_archive, staged_archive_path, create_archive_preview
from .services.import_executor import execute_bulk_import

from apps.assessments.services.video_processor import VideoProcessor
from apps.assessments.services.pose_estimator import PoseEstimator

import cv2

class ParticipantViewSet(viewsets.ModelViewSet):
    queryset = Participant.objects.all().order_by("participant_code")
    serializer_class = ParticipantSerializer
    permission_classes = [permissions.IsAdminUser]

class ViewAngleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ViewAngle.objects.all()
    serializer_class = ViewAngleSerializer
    permission_classes = [permissions.IsAdminUser]

class DatasetViewSet(viewsets.ModelViewSet):
    @action(
        detail=True,
        methods=["post"],
        url_path="retry",
    )

    def retry(self, request, pk=None):
        dataset = self.get_object()

        if dataset.status not in ["FAILED", "PROCESSING"]:
            return Response(
                {
                    "detail": (
                        "Only FAILED or PROCESSING datasets "
                        "can be retried."
                    )
                },
                status=400,
            )

        dataset.status="PENDING"
        dataset.error_message=""
        dataset.save(update_fields=["status", "error_message"])

        process_dataset_video_task.delay(
            dataset.id,
            request.user.id,
        )

        return Response(
            self.get_serializer(dataset).data,
            status=202,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="annotation"
    )
    def annotation(self, request, pk=None):
        dataset = self.get_object()

        samples = (
            dataset.samples
            .select_related("rep_assessment")
            .order_by("rep_assessment__rep_number")
        )

        fps = 0.0

        if dataset.video_file:
            cap = cv2.VideoCapture(dataset.video_file.path)

            try:
                fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            finally:
                cap.release()

        return Response({
            "dataset": self.get_serializer(dataset).data,
            "fps": fps,
            "samples": DatasetSampleSerializer(
                samples,
                many=True,
                context={"request": request},
            ).data,
        })

    lookup_value_regex = r"\d+"
    queryset = Dataset.objects.all().order_by('-created_at')
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAdminUser]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def perform_create(self, serializer):
        dataset = serializer.save(status='PENDING')
        process_dataset_video_task.delay(dataset.id, self.request.user.id)

    def get_serializer_context(self):
        return {'request': self.request}

class DatasetSampleViewSet(viewsets.ModelViewSet):
    queryset = DatasetSample.objects.all()
    serializer_class = DatasetSampleSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        dataset_id = self.request.query_params.get("dataset")

        if dataset_id:
            queryset = queryset.filter(
                dataset_id=dataset_id
            )

        return queryset

    def perform_update(self, serializer):
        label = serializer.validated_data.get(
            "is_correct",
            serializer.instance.is_correct,
        )

        if label is None:
            serializer.save(
                annotator=None,
                annotated_at=None,
            )
        else:
            serializer.save(
                annotator=self.request.user,
                annotated_at=timezone.now(),
            )

class DatasetVideoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DatasetVideo.objects.select_related(
        "dataset",
        "participant",
        "view_angle"
    ).all()

    serializer_class = DatasetVideoSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()
        dataset_id = self.request.query_params.get("dataset")

        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)

        return queryset

class DatasetBulkImportView(APIView):
    def post(self, request):
        serializer = DatasetBulkImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = execute_bulk_import(
            validated_data=serializer.validated_data,
            user=request.user,
        )

        return Response(result, status=status.HTTP_201_CREATED) 

class DatasetImportPreviewView(APIView):
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("zip_file")

        if not uploaded_file:
            return Response(
                {"zip_file": "A ZIP archive is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = create_archive_preview(
            uploaded_file=uploaded_file,
            user=request.user
        )

        return Response(result, status=status.HTTP_200_OK)