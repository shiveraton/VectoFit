import logging
from typing import Any, ClassVar

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

from apps.analytics.services.analysis_engine import analyze
from apps.analytics.services.features import (
    FEATURE_SCHEMA_VERSION,
    FeatureExtractionError,
    extract_rep_features,
)
from apps.analytics.services.segmentation import (
    segment_reps,
    split_contiguous_pose_runs,
)
from apps.analytics.services.session_report import build_session_report
from apps.training.services.model_inference import (
    ModelInferenceError,
    predict_with_active_model,
)

from .models import AssessmentSession, BodyProfile, RepAssessment
from .serializers import (
    AssessmentSessionDetailSerializer,
    AssessmentSessionSerializer,
    BodyProfileSerializer,
    MorphologicalCalibrationRequestSerializer,
    RepAssessmentSerializer,
)
from .services.snapshot_overlay import (
    draw_skeleton,
    reference_landmarks,
    reference_template_from_profile,
)
from .services.video_processor import VideoProcessor

logger = logging.getLogger(__name__)


def _scale_factor_for_session(session):
    if session is None or session.body_profile_id is None:
        return None

    return session.body_profile.scale_factor or None


def _split_contiguous_pose_runs(
    landmark_data: list[dict[str, Any]],
    expected_frame_step: int,
) -> list[list[dict[str, Any]]]:
    return split_contiguous_pose_runs(
        landmark_data,
        expected_frame_step,
    )


def _collect_repetition_entries(
    session_id: int,
    landmark_data: list[dict[str, Any]],
    expected_frame_step: int,
) -> list[dict[str, Any]]:
    pose_runs = _split_contiguous_pose_runs(
        landmark_data,
        expected_frame_step=expected_frame_step,
    )

    repetition_entries: list[dict[str, Any]] = []

    run_gaps = [
        (previous[-1]["frame_index"], current[0]["frame_index"])
        for previous, current in zip(pose_runs, pose_runs[1:])
    ]
    logger.info(
        "[RepCount] session=%s pose_runs=%s run_lengths=%s "
        "run_ranges=%s gaps=%s",
        session_id,
        len(pose_runs),
        [len(run) for run in pose_runs],
        [
            (run[0]["frame_index"], run[-1]["frame_index"])
            for run in pose_runs
        ],
        run_gaps,
    )

    for run_index, run in enumerate(pose_runs, start=1):
        if len(run) < 3:
            continue

        landmark_series = [entry["landmarks"] for entry in run]

        repetitions = segment_reps(landmark_series)

        logger.info(
            "[RepCount] session=%s run=%s frames=%s reps=%s",
            session_id,
            run_index,
            len(run),
            len(repetitions),
        )

        for repetition in repetitions:
            try:
                start_index = int(repetition["start"])
                bottom_index = int(repetition["bottom"])
                end_index = int(repetition["end"])
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"Invalid repetition boundaries: {repetition}"
                ) from exc

            if not (0 <= start_index <= bottom_index <= end_index < len(run)):
                raise RuntimeError(f"Invalid repetition range: {repetition}")

            rep_entries = run[start_index : end_index + 1]

            if rep_entries:
                repetition_entries.append(
                    {
                        "entries": rep_entries,
                        "key_frame_index": rep_entries[bottom_index - start_index][
                            "frame_index"
                        ],
                    }
                )

    if not repetition_entries:
        raise RuntimeError("No complete squat repetitions were detected.")

    return repetition_entries


def _prepare_assessments(
    session: AssessmentSession,
    repetition_entries: list[dict[str, Any]],
    thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    prepared_assessments: list[dict[str, Any]] = []

    for rep_number, rep_entry in enumerate(
        repetition_entries,
        start=1,
    ):
        entries = rep_entry["entries"]
        rep_landmarks = [entry["landmarks"] for entry in entries]

        analysis_result = analyze(
            rep_landmarks,
            thresholds,
        )

        reference_template = reference_template_from_profile(
            session.body_profile,
            session.view_angle,
            next(
                (
                    entry.get("landmarks")
                    for entry in entries
                    if entry.get("frame_index") == rep_entry["key_frame_index"]
                ),
                entries[len(entries) // 2].get("landmarks") if entries else None,
            ),
        )
        if reference_template is not None:
            analysis_result["reference_template"] = reference_template

        model_prediction = {
            "status": "not_assessed",
            "reason": None,
        }

        if not session.view_angle:
            model_prediction["reason"] = "missing_view_angle"
        else:
            try:
                features = extract_rep_features(
                    rep_landmarks,
                    fps=30.0,
                    scale_factor=_scale_factor_for_session(session),
                )

                model_prediction = predict_with_active_model(
                    features=features,
                    view_angle=session.view_angle,
                    prediction_target="binary_form",
                    feature_schema_version=FEATURE_SCHEMA_VERSION,
                )

            except FeatureExtractionError as exc:
                model_prediction = {
                    "status": "not_assessed",
                    "reason": "feature_extraction_failed",
                    "detail": str(exc),
                }

            except ModelInferenceError as exc:
                model_prediction = {
                    "status": "not_assessed",
                    "reason": "model_inference_failed",
                    "detail": str(exc),
                    **exc.payload,
                }

        analysis_result["model_prediction"] = model_prediction

        prepared_assessments.append(
            {
                "rep_number": rep_number,
                "landmark_series": rep_landmarks,
                "asymmetry_series": analysis_result.get("asymmetry_series"),
                "start_frame": entries[0]["frame_index"],
                "end_frame": entries[-1]["frame_index"],
                "key_frame_index": rep_entry["key_frame_index"],
                "analysis_result": analysis_result,
            }
        )

    return prepared_assessments


def _save_assessments(
    session: AssessmentSession,
    prepared_assessments: list[dict[str, Any]],
) -> None:
    with transaction.atomic():
        RepAssessment.objects.filter(session=session).delete()

        for assessment in prepared_assessments:
            RepAssessment.objects.create(
                session=session,
                rep_number=assessment["rep_number"],
                landmark_series=assessment["landmark_series"],
                asymmetry_series=assessment["asymmetry_series"],
                start_frame=assessment["start_frame"],
                end_frame=assessment["end_frame"],
                key_frame_index=assessment["key_frame_index"],
                analysis_result=assessment["analysis_result"],
            )

    logger.info(
        "[RepCount] session=%s saved_reps=%s",
        session.pk,
        len(prepared_assessments),
    )


def _generate_session_report(
    session: AssessmentSession,
    thresholds: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        return build_session_report(
            session.reps.all(),
            thresholds,
        )
    except Exception:
        logger.exception(
            "Session report generation failed for session=%s",
            session.pk,
        )
        return None


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

    if height_value is None:
        height_value = 170.0

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
        self._process_session(session)

    def _process_session(self, session: AssessmentSession) -> None:
        session.status = AssessmentSession.Status.PROCESSING
        session.error_message = ""
        session.report = None

        session.save(
            update_fields=[
                "status",
                "error_message",
                "report",
            ],
        )

        try:
            result = VideoProcessor.process_video(
                session.video_file.path,
            )

            if result.get("status") != "success":
                raise ValueError(result.get("message", "Video processing failed."))

            landmark_data = result.get("landmark_data", [])

            if not landmark_data:
                raise RuntimeError("No landmark frames were produced from the video.")

            valid_pose_frames = sum(
                bool(entry.get("landmarks")) for entry in landmark_data
            )
            logger.info(
                "[RepCount] session=%s extraction=%s sampled=%s valid_pose=%s "
                "valid_pct=%.1f fps=%s source_resolution=%sx%s",
                session.pk,
                result.get("status"),
                len(landmark_data),
                valid_pose_frames,
                valid_pose_frames / len(landmark_data) * 100,
                result.get("native_fps"),
                result.get("source_width"),
                result.get("source_height"),
            )

            if valid_pose_frames == 0:
                raise RuntimeError(
                    "Pose extraction failed: no valid pose landmarks were detected."
                )

            native_fps = float(result.get("native_fps") or 30.0)

            if not np.isfinite(native_fps) or native_fps <= 0:
                native_fps = 30.0

            expected_frame_step = max(
                1,
                round(native_fps / 30.0),
            )

            repetition_entries = _collect_repetition_entries(
                session_id=session.pk,
                landmark_data=landmark_data,
                expected_frame_step=expected_frame_step,
            )

            thresholds = session.exercise_variant.get_thresholds()

            prepared_assessments = _prepare_assessments(
                session,
                repetition_entries,
                thresholds,
            )

            _save_assessments(
                session,
                prepared_assessments,
            )

            session.report = _generate_session_report(
                session,
                thresholds,
            )

            session.status = AssessmentSession.Status.COMPLETED
            session.error_message = ""

        except Exception as exc:
            logger.exception(
                "Assessment processing failed for session=%s",
                session.pk,
            )

            # A failed run must not expose stale or partially written reps.
            RepAssessment.objects.filter(session=session).delete()

            session.status = AssessmentSession.Status.FAILED
            session.error_message = str(exc)
            session.report = None

        finally:
            session.processed_at = timezone.now()

            session.save(
                update_fields=[
                    "status",
                    "error_message",
                    "processed_at",
                    "report",
                ],
            )


class RepAssessmentViewSet(viewsets.ModelViewSet):
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
        draw_skeleton(
            frame, reference_landmarks(rep), (0, 220, 0), thickness=5, dashed=True
        )

        encoded, buffer = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82]
        )
        if not encoded:
            return Response(
                {"detail": "The representative frame could not be encoded."}, status=500
            )
        return HttpResponse(buffer.tobytes(), content_type="image/jpeg")
