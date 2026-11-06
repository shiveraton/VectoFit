import logging
from typing import ClassVar

import cv2
import numpy as np
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import BaseParser, FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AssessmentSession, BodyProfile, RepAssessment
from .serializers import (
    AssessmentSessionDetailSerializer,
    AssessmentSessionSerializer,
    BodyProfileSerializer,
    MorphologicalCalibrationRequestSerializer,
    RepAssessmentSerializer,
)
from .services.snapshot_overlay import (
    draw_fppa_overlay,
    draw_skeleton,
)

logger = logging.getLogger(__name__)


def _enqueue_assessment_processing(session_id: int) -> None:
    from .tasks import process_assessment_session

    try:
        process_assessment_session.delay(session_id)
    except Exception as exc:
        logger.exception("Could not enqueue assessment session=%s", session_id)
        AssessmentSession.objects.filter(
            pk=session_id,
            status=AssessmentSession.Status.PENDING,
        ).update(
            status=AssessmentSession.Status.FAILED,
            error_message=f"Could not queue assessment processing: {exc}",
            processed_at=timezone.now(),
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_morphological_calibration(request):
    serializer = MorphologicalCalibrationRequestSerializer(
        data=request.data,
    )

    if not serializer.is_valid():
        return Response(
            {
                "detail": "Invalid calibration payload",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    validated_data = serializer.validated_data
    landmarks = validated_data["landmarks"]
    profile_input = validated_data.get("body_profile_data") or {}

    height_value = profile_input.get("height_cm")

    if height_value is None:
        height_value = profile_input.get("height")

    try:
        user_height_cm = float(height_value)
    except (TypeError, ValueError):
        return Response(
            {"detail": "Height must be a valid positive number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not np.isfinite(user_height_cm) or user_height_cm <= 0:
        return Response(
            {"detail": "Height must be a valid positive number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        landmark_map = {
            int(landmark.get("id", index)): landmark
            for index, landmark in enumerate(landmarks)
        }
    except (AttributeError, TypeError, ValueError):
        return Response(
            {"detail": "Invalid landmark identifiers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    required_indices = [11, 12, 23, 24, 25, 26, 27, 28]

    if not all(index in landmark_map for index in required_indices):
        return Response(
            {"detail": ("Insufficient keypoint data for calibration.")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get_point(index: int) -> np.ndarray:
        landmark = landmark_map[index]

        point = np.asarray(
            [
                landmark["x_coordinate"],
                landmark["y_coordinate"],
            ],
            dtype=np.float64,
        )

        if not np.isfinite(point).all():
            raise ValueError(f"Landmark {index} contains invalid coordinates.")

        return point

    try:
        left_shoulder = get_point(11)
        right_shoulder = get_point(12)

        left_hip = get_point(23)
        right_hip = get_point(24)

        left_knee = get_point(25)
        right_knee = get_point(26)

        left_ankle = get_point(27)
        right_ankle = get_point(28)

    except (KeyError, TypeError, ValueError) as exc:
        return Response(
            {"detail": str(exc) or "Invalid landmark coordinates."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    shoulder_midpoint = (left_shoulder + right_shoulder) / 2.0
    hip_midpoint = (left_hip + right_hip) / 2.0

    torso_px = float(np.linalg.norm(shoulder_midpoint - hip_midpoint))

    left_femur_px = float(np.linalg.norm(left_hip - left_knee))
    right_femur_px = float(np.linalg.norm(right_hip - right_knee))

    left_tibia_px = float(np.linalg.norm(left_knee - left_ankle))
    right_tibia_px = float(np.linalg.norm(right_knee - right_ankle))

    avg_femur_px = (left_femur_px + right_femur_px) / 2.0

    avg_tibia_px = (left_tibia_px + right_tibia_px) / 2.0

    total_body_px = torso_px + avg_femur_px + avg_tibia_px

    if not np.isfinite(total_body_px) or total_body_px <= 0:
        return Response(
            {
                "detail": (
                    "Calibration landmarks do not produce valid body-segment lengths."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    scale_factor = float(total_body_px / (user_height_cm / 100.0))

    torso_cm = round(
        (torso_px / scale_factor) * 100.0,
        2,
    )

    left_femur_cm = round(
        (left_femur_px / scale_factor) * 100.0,
        2,
    )

    right_femur_cm = round(
        (right_femur_px / scale_factor) * 100.0,
        2,
    )

    avg_femur_cm = round(
        (left_femur_cm + right_femur_cm) / 2.0,
        2,
    )

    avg_tibia_cm = round(
        (avg_tibia_px / scale_factor) * 100.0,
        2,
    )

    body_profile, _ = BodyProfile.objects.update_or_create(
        user=request.user,
        defaults={
            "height_cm": user_height_cm,
            "torso_length_cm": torso_cm,
            "femur_length_cm": avg_femur_cm,
            "tibia_length_cm": avg_tibia_cm,
            "scale_factor": scale_factor,
            "raw_calibration_data": landmarks,
        },
    )

    return Response(
        {
            "status": "VALIDATED",
            "scale_factor_px_per_m": scale_factor,
            "segment_lengths": {
                "torso_cm": torso_cm,
                "left_femur_cm": left_femur_cm,
                "right_femur_cm": right_femur_cm,
            },
            "profile": BodyProfileSerializer(body_profile).data,
        },
        status=status.HTTP_200_OK,
    )


class BodyProfileViewSet(viewsets.ModelViewSet):
    serializer_class = BodyProfileSerializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BodyProfile.objects.filter(
            user=self.request.user,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AssessmentSessionViewSet(viewsets.ModelViewSet):
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]
    parser_classes: ClassVar[list[type[BaseParser]]] = [FormParser, MultiPartParser]

    def get_queryset(self):
        queryset = (
            AssessmentSession.objects.filter(user=self.request.user)
            .select_related(
                "exercise_variant",
                "body_profile",
            )
            .annotate(
                rep_count=Count("reps"),
            )
        )

        include_reps = (
            self.action == "retrieve"
            and self.request.query_params.get("include") == "reps"
        )

        if include_reps:
            detail_reps = RepAssessment.objects.only(
                "id",
                "session_id",
                "rep_number",
                "jaa_score",
                "rom_score",
                "bad_score",
                "kvt_score",
                "hybrid_score",
                "classification",
                "analysis_result",
                "landmark_series",
                "asymmetry_series",
                "start_frame",
                "end_frame",
                "key_frame_index",
            )

            queryset = queryset.prefetch_related(
                Prefetch("reps", queryset=detail_reps),
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AssessmentSessionDetailSerializer

        return AssessmentSessionSerializer

    def perform_create(self, serializer):
        profile = (
            BodyProfile.objects.filter(user=self.request.user)
            .order_by("-calibrated_at")
            .first()
        )
        session = serializer.save(user=self.request.user, body_profile=profile)
        session.status = AssessmentSession.Status.PENDING
        session.save(update_fields=["status"])
        transaction.on_commit(
            lambda session_id=session.pk: _enqueue_assessment_processing(session_id)
        )
        session.refresh_from_db()

    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request, pk=None):
        session = self.get_object()
        if session.status != AssessmentSession.Status.FAILED:
            return Response(
                {"detail": "Only failed assessment sessions can be retried."},
                status=status.HTTP_409_CONFLICT,
            )

        session.status = AssessmentSession.Status.PENDING
        session.error_message = ""
        session.processed_at = None
        session.save(update_fields=["status", "error_message", "processed_at"])
        transaction.on_commit(
            lambda session_id=session.pk: _enqueue_assessment_processing(session_id)
        )
        session.refresh_from_db()
        return Response(self.get_serializer(session).data, status=status.HTTP_202_ACCEPTED)



class RepAssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RepAssessmentSerializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RepAssessment.objects.filter(
            session__user=self.request.user,
        )

    @action(detail=True, methods=["get"], url_path="snapshot")
    def snapshot(self, request, pk=None):
        rep = self.get_object()
        session = rep.session
        if not session.video_file:
            return Response({"detail": "No source video is available."}, status=404)

        frame_index = rep.key_frame_index
        if frame_index is None:
            frame_index = rep.start_frame
            if rep.end_frame is not None and frame_index is not None:
                frame_index = (frame_index + rep.end_frame) // 2
        if frame_index is None:
            return Response(
                {"detail": "No representative frame is available."}, status=404
            )

        try:
            source_path = session.video_file.path
        except (AttributeError, ValueError, OSError):
            return Response({"detail": "The source video is unavailable."}, status=404)

        capture = cv2.VideoCapture(source_path)
        try:
            if not capture.isOpened():
                return Response(
                    {"detail": "The source video could not be opened."}, status=404
                )
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            success, frame = capture.read()
        finally:
            capture.release()

        if not success or frame is None:
            return Response(
                {"detail": "The representative frame could not be read."}, status=404
            )

        observed = None
        series = rep.landmark_series or []
        for entry in series:
            if isinstance(entry, dict) and entry.get("frame_index") == frame_index:
                observed = entry.get("landmarks")
                break
        if observed is None and series:
            offset = None
            if (
                rep.start_frame is not None
                and rep.end_frame is not None
                and len(series) > 1
            ):
                span = rep.end_frame - rep.start_frame
                if span >= 0 and span % (len(series) - 1) == 0:
                    step = span // (len(series) - 1)
                    if step > 0 and (frame_index - rep.start_frame) % step == 0:
                        candidate = (frame_index - rep.start_frame) // step
                        if 0 <= candidate < len(series):
                            offset = candidate
            if offset is None and rep.key_frame_index is None:
                offset = len(series) // 2
            if offset is None and rep.start_frame is not None:
                candidate = frame_index - rep.start_frame
                if 0 <= candidate < len(series):
                    offset = candidate
            if offset is not None:
                observed = series[offset]

        draw_skeleton(frame, observed, (0, 0, 255), thickness=4)
        analysis_result = rep.analysis_result or {}
        draw_fppa_overlay(frame, observed, analysis_result.get("fppa"))

        encoded, buffer = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82]
        )
        if not encoded:
            return Response(
                {"detail": "The representative frame could not be encoded."}, status=500
            )
        return HttpResponse(buffer.tobytes(), content_type="image/jpeg")
