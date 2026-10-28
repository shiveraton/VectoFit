from typing import ClassVar

import cv2
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import BaseParser, FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Dataset, DatasetSample, DatasetVideo, Participant, ViewAngle
from .serializers import (
    DatasetBulkImportSerializer,
    DatasetSampleSerializer,
    DatasetSerializer,
    DatasetVideoSerializer,
    ParticipantSerializer,
    ViewAngleSerializer,
)
from .services.bulk_import import create_archive_preview
from .services.import_executor import execute_bulk_import
from .services.tasks import process_dataset_video_task


class ParticipantViewSet(viewsets.ModelViewSet):
    queryset = Participant.objects.all().order_by("participant_code")
    serializer_class = ParticipantSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]


class ViewAngleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ViewAngle.objects.all()
    serializer_class = ViewAngleSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]


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
                {"detail": ("Only FAILED or PROCESSING datasets can be retried.")},
                status=400,
            )

        dataset.status = "PENDING"
        dataset.error_message = ""
        dataset.save(update_fields=["status", "error_message"])

        process_dataset_video_task.delay(
            dataset.id,
            request.user.id,
        )

        return Response(
            self.get_serializer(dataset).data,
            status=202,
        )

    @action(detail=True, methods=["get"], url_path="annotation")
    def annotation(self, request, pk=None):
        dataset = self.get_object()

        samples = dataset.samples.select_related(
            "rep_assessment",
            "dataset_video__participant",
            "dataset_video__view_angle",
        )
        if dataset.videos.exists():
            samples = samples.filter(dataset_video__requires_manual_review=True)

        samples = samples.order_by(
            "dataset_video__participant__participant_code",
            Case(
                When(
                    dataset_video__view_angle__angle_variant="diagonal", then=Value(0)
                ),
                When(dataset_video__view_angle__angle_variant="frontal", then=Value(1)),
                When(
                    dataset_video__view_angle__angle_variant="sagittal", then=Value(2)
                ),
                default=Value(3),
                output_field=IntegerField(),
            ),
            Case(
                When(dataset_video__source_label=True, then=Value(0)),
                When(dataset_video__source_label=False, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            ),
            "dataset_video_id",
            "rep_assessment__rep_number",
            "id",
        )

        def read_fps(video_file):
            if not video_file:
                return 0.0
            try:
                cap = cv2.VideoCapture(video_file.path)
                try:
                    return float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
                finally:
                    cap.release()
            except (OSError, cv2.error):
                return 0.0

        legacy_fps = read_fps(dataset.video_file)
        fps_by_video_id = {}
        for sample in samples:
            if (
                sample.dataset_video_id
                and sample.dataset_video_id not in fps_by_video_id
            ):
                fps_by_video_id[sample.dataset_video_id] = read_fps(
                    sample.dataset_video.video_file
                )

        return Response(
            {
                "dataset": self.get_serializer(dataset).data,
                "fps": legacy_fps,
                "samples": DatasetSampleSerializer(
                    samples,
                    many=True,
                    context={"request": request, "video_fps_by_id": fps_by_video_id},
                ).data,
            }
        )

    lookup_value_regex = r"\d+"
    queryset = Dataset.objects.all().order_by("-created_at")
    serializer_class = DatasetSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def perform_create(self, serializer):
        dataset = serializer.save(status="PENDING")
        process_dataset_video_task.delay(dataset.id, self.request.user.id)

    def get_serializer_context(self):
        return {"request": self.request}


class DatasetSampleViewSet(viewsets.ModelViewSet):
    queryset = DatasetSample.objects.all()
    serializer_class = DatasetSampleSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        dataset_id = self.request.query_params.get("dataset")

        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)

        return queryset

    def perform_update(self, serializer):
        if "is_correct" not in serializer.validated_data:
            serializer.save()
            return

        label = serializer.validated_data.get(
            "is_correct",
            serializer.instance.is_correct,
        )

        if label is None:
            video = serializer.instance.dataset_video
            base_label = (
                None
                if video is not None and video.requires_manual_review
                else video.source_label
                if video is not None
                else None
            )
            serializer.save(
                is_correct=base_label,
                error_label="",
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
        "dataset", "participant", "view_angle"
    ).all()

    serializer_class = DatasetVideoSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

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

        return Response(
            {
                "dataset": DatasetSerializer(
                    result["dataset"], context={"request": request}
                ).data,
                "imported_videos": result["imported_videos"],
                "queued_videos": result["queued_videos"],
                "queue_failures": result["queue_failures"],
            },
            status=status.HTTP_201_CREATED,
        )


class DatasetImportPreviewView(APIView):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]
    parser_classes: ClassVar[list[type[BaseParser]]] = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("zip_file")

        if not uploaded_file:
            return Response(
                {"zip_file": "A ZIP archive is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = create_archive_preview(uploaded_file=uploaded_file, user=request.user)

        return Response(result, status=status.HTTP_200_OK)
