from typing import ClassVar

import cv2
from django.conf import settings
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import BaseParser, FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AnnotationEvent,
    Dataset,
    DatasetAnnotatorAssignment,
    DatasetSample,
    DatasetVideo,
    KneeAnnotation,
    Participant,
    ViewAngle,
)
from .permissions import IsAnnotatorOrAdmin
from .serializers import (
    AnnotationEventSerializer,
    DatasetAnnotatorAssignmentSerializer,
    DatasetBulkImportSerializer,
    DatasetSampleSerializer,
    DatasetSerializer,
    DatasetVideoSerializer,
    ParticipantSerializer,
    ViewAngleSerializer,
)
from .services.agreement import agreement_for_dataset
from .services.bulk_import import create_archive_preview
from .services.consensus import base_label_for_sample, evaluate_sample
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
    def get_permissions(self):
        if self.action in {
            "annotation",
            "annotation_queue",
            "retrieve",
            "list",
        }:
            return [IsAnnotatorOrAdmin()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        queryset = Dataset.objects.all().order_by("-created_at")
        user = self.request.user

        if not user.is_authenticated or user.is_staff:
            return queryset

        return queryset.filter(
            annotator_assignments__annotator=user,
            annotator_assignments__is_active=True,
        ).distinct()

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
        samples = self._annotation_samples(dataset)

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
                "annotator_name": request.user.get_username(),
                "fps": legacy_fps,
                "samples": DatasetSampleSerializer(
                    samples,
                    many=True,
                    context={"request": request, "video_fps_by_id": fps_by_video_id},
                ).data,
            }
        )

    def _annotation_samples(self, dataset):
        samples = dataset.samples.select_related(
            "rep_assessment",
            "dataset_video__participant",
            "dataset_video__view_angle",
        )
        if dataset.videos.exists():
            samples = samples.filter(
                dataset_video__requires_manual_review=True,
                dataset_video__view_angle__angle_variant="frontal",
            )

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

        return samples

    @action(detail=False, methods=["get"], url_path="annotation-queue")
    def annotation_queue(self, request):
        data = []
        for dataset in self.get_queryset():
            samples = self._annotation_samples(dataset)
            ids = list(samples.values_list("id", flat=True))
            total = len(ids)
            mine = KneeAnnotation.objects.filter(
                sample_id__in=ids, annotator=request.user
            ).count()
            data.append(
                {
                    "id": dataset.pk,
                    "name": dataset.name,
                    "description": dataset.description,
                    "exercise_type": dataset.exercise_type,
                    "purpose": dataset.purpose,
                    "status": dataset.status,
                    "review_total": total,
                    "annotated_by_me": mine,
                    "pending_for_me": max(total - mine, 0),
                }
            )
        return Response(data)

    @action(detail=True, methods=["get"], url_path="annotation-history")
    def annotation_history(self, request, pk=None):
        dataset = self.get_object()
        rows = AnnotationEvent.objects.filter(sample__dataset=dataset).select_related(
            "annotator", "entered_by"
        )
        for key in ("sample", "annotator", "action"):
            value = request.query_params.get(key)
            if value:
                rows = rows.filter(**{f"{key}_id" if key != "action" else key: value})
        paginator = LimitOffsetPagination()
        paginator.default_limit = 100
        page = paginator.paginate_queryset(
            rows.order_by("-created_at"), request, view=self
        )
        return paginator.get_paginated_response(
            AnnotationEventSerializer(page, many=True).data
        )

    @action(detail=True, methods=["get"], url_path="consensus")
    def consensus(self, request, pk=None):
        dataset = self.get_object()
        results = [(s, evaluate_sample(s)) for s in dataset.samples.all()]
        return Response(
            {
                "counts": {
                    status: sum(r["status"] == status for _, r in results)
                    for status in (
                        "resolved",
                        "insufficient",
                        "disagreement",
                        "not_trainable",
                    )
                },
                "needs_adjudication": [
                    sample.pk
                    for sample, result in results
                    if result["status"] in {"disagreement", "not_trainable"}
                ],
            }
        )

    @action(detail=True, methods=["get"], url_path="agreement")
    def agreement(self, request, pk=None):
        return Response(agreement_for_dataset(self.get_object()))

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

    def get_permissions(self):
        if self.action in [
            "list",
            "retrieve",
            "update",
            "partial_update",
            "save_annotation",
            "clear_annotation",
        ]:
            permission_classes = [IsAnnotatorOrAdmin]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()

        user = self.request.user
        dataset_id = self.request.query_params.get("dataset")

        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)

        if not user.is_staff:
            queryset = queryset.filter(
                annotator_assignments__annotator=user,
                annotator_assignments__is_active=True,
            ).distinct()

        return queryset

    def perform_update(self, serializer):
        if not self.request.user.is_staff and set(self.request.data) - {
            "knee_annotation"
        }:
            raise PermissionDenied("Annotators may only change their knee annotation.")
        if "is_correct" not in serializer.validated_data:
            serializer.save()
            return

        label = serializer.validated_data.get(
            "is_correct",
            serializer.instance.is_correct,
        )

        if label is None:
            base_label = base_label_for_sample(serializer.instance)
            serializer.save(
                is_correct=base_label,
                error_label="",
                annotator=None,
                annotated_at=None,
                label_source="",
            )
        else:
            serializer.save(
                annotator=self.request.user,
                annotated_at=timezone.now(),
                label_source="adjudicated",
            )

    @action(detail=True, methods=["post"], url_path="adjudicate")
    def adjudicate(self, request, pk=None):
        sample = self.get_object()
        target = request.data.get("target_label")
        mapping = getattr(
            settings, "ANNOTATION_TARGET_TO_IS_CORRECT", {"good": True, "bad": False}
        )
        if target not in mapping:
            return Response({"target_label": "Expected good or bad."}, status=400)
        sample.is_correct = mapping[target]
        sample.label_source = "adjudicated"
        sample.annotator = request.user
        sample.annotated_at = timezone.now()
        sample.save(
            update_fields=["is_correct", "label_source", "annotator", "annotated_at"]
        )
        AnnotationEvent.objects.create(
            sample=sample,
            annotator=request.user,
            entered_by=request.user,
            action=AnnotationEvent.Action.ADJUDICATE,
            target_label=target,
            payload={"target_label": target, "note": request.data.get("note", "")},
            rubric_version=getattr(settings, "ANNOTATION_RUBRIC_VERSION", "v1"),
        )
        return Response(
            DatasetSampleSerializer(sample, context={"request": request}).data
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


class DatasetAnnotatorAssignmentViewSet(viewsets.ModelViewSet):
    queryset = DatasetAnnotatorAssignment.objects.select_related(
        "annotator", "dataset", "assigned_by"
    ).order_by("dataset_id", "annotator__username")
    serializer_class = DatasetAnnotatorAssignmentSerializer
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        dataset_id = self.request.query_params.get("dataset")
        annotator_id = self.request.query_params.get("annotator")

        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        if annotator_id:
            queryset = queryset.filter(annotator_id=annotator_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        from django.contrib.auth import get_user_model
        from django.db import transaction

        from apps.accounts.roles import is_annotator

        dataset_id = request.data.get("dataset")
        annotator_ids = request.data.get("annotators") or []

        if not dataset_id:
            return Response(
                {"dataset": "Select a dataset."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(annotator_ids, list) or not annotator_ids:
            return Response(
                {"annotators": "Select at least one annotator."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = Dataset.objects.filter(pk=dataset_id).first()
        if dataset is None:
            return Response(
                {"dataset": "That dataset does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        User = get_user_model()
        users = list(User.objects.filter(pk__in=annotator_ids))
        invalid = [user.username for user in users if not is_annotator(user)]
        if invalid:
            return Response(
                {"annotators": f"Not annotators: {', '.join(invalid)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = 0
        reactivated = 0
        with transaction.atomic():
            for user in users:
                assignment, was_created = (
                    DatasetAnnotatorAssignment.objects.get_or_create(
                        dataset=dataset,
                        annotator=user,
                        defaults={"assigned_by": request.user, "is_active": True},
                    )
                )
                if was_created:
                    created += 1
                elif not assignment.is_active:
                    assignment.is_active = True
                    assignment.assigned_by = request.user
                    assignment.save(update_fields=["is_active", "assigned_by"])
                    reactivated += 1

        return Response(
            {
                "created": created,
                "reactivated": reactivated,
                "total": self.get_queryset().filter(dataset=dataset).count(),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="unassign")
    def unassign(self, request):
        dataset_id = request.data.get("dataset")
        annotator_id = request.data.get("annotator")

        if not dataset_id or not annotator_id:
            return Response(
                {"detail": "dataset and annotator are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = DatasetAnnotatorAssignment.objects.filter(
            dataset_id=dataset_id, annotator_id=annotator_id
        ).delete()

        return Response({"deleted": deleted}, status=status.HTTP_200_OK)


class DatasetBulkImportView(APIView):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

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
