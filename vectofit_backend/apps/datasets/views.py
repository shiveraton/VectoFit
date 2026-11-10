from apps.analytics.utils.file_resolver import resolved_video_path, VideoResolutionError
from typing import ClassVar
import logging

import cv2
from django.db import transaction
from django.db.models import Case, IntegerField, Prefetch, Q, Value, When
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import BaseParser, FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Dataset,
    DatasetSample,
    DatasetVideo,
    KneeAnnotation,
    Participant,
    ViewAngle,
)
from .serializers import (
    DatasetBulkImportSerializer,
    DatasetListSerializer,
    DatasetSampleSerializer,
    DatasetSerializer,
    DatasetVideoSerializer,
    ParticipantSerializer,
    ViewAngleSerializer,
)
from .services.bulk_import import create_archive_preview
from .services.import_executor import execute_bulk_import
from .services.tasks import process_dataset_video_task
from .permissions import IsAnnotator
from .services.assignments import assigned_review_samples, assigned_samples, review_samples
from .services.knee_label import final_knee_target

logger = logging.getLogger(__name__)


def _enqueue_dataset_processing(dataset_id: int, user_id: int) -> None:
    try:
        process_dataset_video_task.delay(dataset_id, user_id)
    except Exception as exc:
        logger.exception("Could not queue dataset processing for dataset=%s", dataset_id)
        Dataset.objects.filter(pk=dataset_id, status="PENDING").update(
            status="FAILED",
            error_message=f"Could not queue dataset processing: {exc}",
        )


def _annotation_review_fields(serializer, user):
    if "knee_annotation" not in serializer.validated_data:
        return {}
    if serializer.validated_data["knee_annotation"] is None:
        return {"annotator": None, "annotated_at": None}
    return {"annotator": user, "annotated_at": timezone.now()}


def _label_review_fields(annotation_changed, label, user):
    if annotation_changed:
        return {}
    if label is None:
        return {"annotator": None, "annotated_at": None}
    return {"annotator": user, "annotated_at": timezone.now()}


class ParticipantViewSet(viewsets.ModelViewSet):
    queryset = Participant.objects.all().order_by("participant_code")
    serializer_class = ParticipantSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]


class ViewAngleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ViewAngle.objects.all()
    serializer_class = ViewAngleSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]


class DatasetViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=["get"], url_path="knee-readiness")
    def knee_readiness(self, request, pk=None):
        from apps.training.services.data_loader import prepare_knee_samples

        samples = prepare_knee_samples([self.get_object()])
        return Response(samples.readiness_report())

    def get_serializer_class(self):
        if self.action == "list":
            return DatasetListSerializer
        return super().get_serializer_class()

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

        transaction.on_commit(
            lambda dataset_id=dataset.id, user_id=request.user.id: _enqueue_dataset_processing(
                dataset_id, user_id
            )
        )
        dataset.refresh_from_db()

        return Response(
            self.get_serializer(dataset).data,
            status=202,
        )

    @action(detail=True, methods=["get"], url_path="annotation")
    def annotation(self, request, pk=None):
        dataset = self.get_object()

        samples = review_samples().filter(dataset=dataset).select_related(
            "rep_assessment",
            "dataset_video__participant",
            "dataset_video__view_angle",
        )
        if not request.user.is_staff:
            samples = samples.filter(pk__in=assigned_review_samples(request.user).values("pk"))

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
                with resolved_video_path(video_file) as video_path:
                    cap = cv2.VideoCapture(video_path)
                    try:
                        return float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
                    finally:
                        cap.release()
            except (OSError, cv2.error, VideoResolutionError):
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

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            samples = DatasetSample.objects.select_related(
                "dataset_video__participant", "dataset_video__view_angle"
            ).prefetch_related(
                Prefetch(
                    "knee_annotation_records",
                    queryset=KneeAnnotation.objects.order_by(
                        "annotator_id", "-created_at", "-id"
                    ),
                    to_attr="prefetched_knee_annotation_records",
                )
            )
            videos = DatasetVideo.objects.select_related("participant", "view_angle")
            queryset = queryset.prefetch_related(
                Prefetch("samples", queryset=samples, to_attr="summary_samples"),
                Prefetch("videos", queryset=videos, to_attr="summary_videos"),
            )
        if self.action == "annotation" and not self.request.user.is_staff:
            queryset = queryset.filter(pk__in=assigned_review_samples(self.request.user).values("dataset_id"))
        return queryset

    lookup_value_regex = r"\d+"
    queryset = Dataset.objects.all().order_by("-created_at")
    serializer_class = DatasetSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get_permissions(self):
        if self.action == "annotation":
            return [IsAnnotator()]
        return super().get_permissions()
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def perform_create(self, serializer):
        dataset = serializer.save(status="PENDING")
        transaction.on_commit(
            lambda dataset_id=dataset.id, user_id=self.request.user.id: _enqueue_dataset_processing(
                dataset_id, user_id
            )
        )
        dataset.refresh_from_db()

    def get_serializer_context(self):
        return {"request": self.request}


class DatasetSampleViewSet(viewsets.ModelViewSet):
    queryset = DatasetSample.objects.all()
    serializer_class = DatasetSampleSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get_permissions(self):
        if self.action in {"partial_update", "update"}:
            return [IsAnnotator()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            if self.action in {"partial_update", "update"}:
                queryset = queryset.filter(pk__in=assigned_samples(self.request.user).values("pk"))
            else:
                queryset = queryset.filter(pk__in=assigned_review_samples(self.request.user).values("pk"))

        dataset_id = self.request.query_params.get("dataset")

        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)

        return queryset

    def perform_update(self, serializer):
        if (
            not self.request.user.is_staff
            and set(serializer.validated_data) != {"knee_annotation"}
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Annotators may only update knee_annotation.")
        annotation_changed = "knee_annotation" in serializer.validated_data
        review_fields = _annotation_review_fields(serializer, self.request.user)

        if "is_correct" not in serializer.validated_data:
            serializer.save(**review_fields)
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
                **(
                    review_fields
                    or _label_review_fields(
                        annotation_changed, label, self.request.user
                    )
                ),
            )
        else:
            serializer.save(
                **(
                    review_fields
                    or _label_review_fields(
                        annotation_changed, label, self.request.user
                    )
                )
            )


class AnnotationPoolView(APIView):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get(self, request):
        datasets = Dataset.objects.all().order_by("-updated_at", "-id")
        response = []

        for dataset in datasets:
            samples = review_samples().filter(dataset=dataset)
            sample_count = samples.count()

            records = list(
                KneeAnnotation.objects.filter(sample__in=samples)
                .select_related("annotator", "sample")
                .order_by("-created_at", "-id")
            )
            latest_records = {}
            for record in records:
                latest_records.setdefault((record.sample_id, record.annotator_id), record)
            reviewed_count = len({record.sample_id for record in latest_records.values()
                                  if record.annotation is not None})
            pending_count = max(0, sample_count - reviewed_count)
            annotator_activity = {}
            for record in records:
                if record.annotator_id is None:
                    annotator_key = "unassigned"
                    annotator = None
                else:
                    annotator_key = str(record.annotator_id)
                    annotator = {
                        "id": record.annotator_id,
                        "username": record.annotator.username,
                    }

                activity = annotator_activity.setdefault(
                    annotator_key,
                    {
                        "annotator": annotator,
                        "activity_count": 0,
                        "last_activity_at": record.created_at,
                    },
                )
                activity["activity_count"] += 1

            if sample_count == 0:
                job_status = "NO_SAMPLES"
            elif pending_count == 0:
                job_status = "COMPLETED"
            elif reviewed_count:
                job_status = "IN_PROGRESS"
            else:
                job_status = "QUEUED"

            response.append(
                {
                    "id": dataset.id,
                    "name": dataset.name,
                    "dataset_status": dataset.status,
                    "job_status": job_status,
                    "sample_count": sample_count,
                    "reviewed_count": reviewed_count,
                    "pending_count": pending_count,
                    "activity_count": len(records),
                    "created_at": dataset.created_at,
                    "updated_at": dataset.updated_at,
                    "last_activity_at": (
                        records[0].created_at if records else dataset.updated_at
                    ),
                    "annotators": list(annotator_activity.values()),
                    "activity": [
                        {
                            "id": record.id,
                            "sample_id": record.sample_id,
                            "annotator": (
                                {
                                    "id": record.annotator_id,
                                    "username": record.annotator.username,
                                }
                                if record.annotator_id
                                else None
                            ),
                            "created_at": record.created_at,
                            "has_annotation": record.annotation is not None,
                            "annotation": record.annotation,
                            "rubric_version": record.rubric_version,
                        }
                        for record in records
                    ],
                }
            )

        return Response(response)


class AnnotationDatasetListView(APIView):
    permission_classes: ClassVar[list] = [IsAnnotator]

    def get(self, request):
        datasets = Dataset.objects.filter(pk__in=review_samples().values("dataset_id")).order_by("name")
        if not request.user.is_staff:
            datasets = datasets.filter(pk__in=assigned_review_samples(request.user).values("dataset_id"))
        return Response(
            [{"id": item.pk, "name": item.name} for item in datasets]
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
