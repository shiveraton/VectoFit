from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Prefetch
from rest_framework import permissions, viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


from .models import BodyProfile, RepAssessment, AssessmentSession
from .serializers import (
    LandmarkInputSerializer,
    BodyProfileDataInputSerializer,
    MorphologicalCalibrationRequestSerializer,
    BodyProfileSerializer, 
    RepAssessmentSerializer, 
    AssessmentSessionSerializer, 
    AssessmentSessionDetailSerializer,
)

from .services.video_processor import VideoProcessor
from apps.analytics.services.segmentation import segment_reps
from apps.analytics.services.analysis_engine import analyze

import numpy as np
import logging

logger = logging.getLogger(__name__)

def _split_contiguous_pose_runs(landmark_data, expected_frame_step):
    runs = []
    current_run = []
    previous_frame_index = None

    for entry in landmark_data:
        landmarks = entry.get("landmarks")
        frame_index = entry.get("frame_index")

        if not landmarks or frame_index is None:
            if current_run:
                runs.append(current_run)

            current_run = []
            previous_frame_index = None
            continue

        frame_index = int(frame_index)

        if (
            current_run and frame_index - previous_frame_index != expected_frame_step
        ):
            runs.append(current_run)
            current_run = []

        current_run.append(entry)
        previous_frame_index = frame_index

    if current_run:
        runs.append(current_run)

    return runs


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_morphological_calibration(request):
    serializer = MorphologicalCalibrationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"detail": "Invalid calibration payload", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    
    validated_data = serializer.validated_data
    landmarks = validated_data["landmarks"]
    profile_input = validated_data.get("body_profile_data", {})

    user_height_cm = profile_input.get("height_cm") or profile_input.get("height") or 170.0

    lm_dict = {lm.get("id", idx): lm for idx, lm in enumerate(landmarks)}

    required_indices = [11, 12, 23, 24, 25, 26, 27, 28]
    if not all(idx in lm_dict for idx in required_indices):
        return Response(
            {"detail": "Insufficient keypoint data for calibration."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get_pt(idx):
        return np.array([lm_dict[idx]["x_coordinate"], lm_dict[idx]["y_coordinate"]])

    l_shoulder, r_shoulder = get_pt(11), get_pt(12)
    l_hip, r_hip = get_pt(23), get_pt(24)
    l_knee, r_knee = get_pt(25), get_pt(26)
    l_ankle, r_ankle = get_pt(27), get_pt(28)

    torso_px = float(np.linalg.norm(((l_shoulder + r_shoulder) / 2.0 ) - ((l_hip + r_hip) / 2.0)))
    left_femur_px = float(np.linalg.norm(l_hip - l_knee))
    right_femur_px = float(np.linalg.norm(r_hip - r_knee))
    left_tibia_px = float(np.linalg.norm(l_knee - l_ankle))
    right_tibia_px = float(np.linalg.norm(r_knee - r_ankle))

    avg_femur_px = (left_femur_px + right_femur_px) / 2.0
    avg_tibia_px = (left_tibia_px + right_tibia_px) / 2.0
    total_body_px = torso_px + avg_femur_px + avg_tibia_px

    scale_factor = float(total_body_px/(user_height_cm/100))

    torso_cm = round((torso_px / scale_factor) * 100.0, 2)
    left_femur_cm = round((left_femur_px / scale_factor) * 100.0, 2)
    right_femur_cm = round((right_femur_px / scale_factor) * 100.0, 2)
    avg_femur_cm = round(((left_femur_cm + right_femur_cm) / 2.0), 2)
    avg_tibia_cm = round(((avg_tibia_px / scale_factor) * 100.0), 2)

    body_profile, _ = BodyProfile.objects.update_or_create(
        user=request.user,
        defaults = {
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BodyProfile.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AssessmentSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [FormParser, MultiPartParser]

    def get_queryset(self):
        queryset = (
            AssessmentSession.objects
            .filter(user=self.request.user)
            .select_related("exercise_variant", "body_profile")
            .annotate(rep_count=Count("reps"))
        )

        if self.action == "retrieve":
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
                "start_frame",
                "end_frame",
            )
            queryset = queryset.prefetch_related(
                Prefetch("reps", queryset=detail_reps)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AssessmentSessionDetailSerializer
        return AssessmentSessionSerializer

    def perform_create(self, serializer):
        session = serializer.save(user=self.request.user)
        self._process_session(session)


    def _process_session(self, session):
        session.status = AssessmentSession.Status.PROCESSING
        session.error_message = ""
        session.save(update_fields=["status", "error_message"])

        try:
            result = VideoProcessor.process_video(session.video_file.path)

            if result.get("status") != "success":
                raise ValueError(
                    result.get("message", "Video processing failed.")
                )

            landmark_data = result.get("landmark_data", [])

            if not landmark_data:
                raise RuntimeError(
                    "No landmark frames were produced from the video."
                )

            native_fps = float(result.get("native_fps") or 30.0)

            if native_fps <= 0:
                native_fps = 30.0

            expected_frame_step = max(
                1,
                round(native_fps / 30.0)
            )

            pose_runs = _split_contiguous_pose_runs(
                landmark_data,
                expected_frame_step=expected_frame_step
            )

            segmented_rep_entries = []

            for run_index, run in enumerate(pose_runs, start=1):
                if len(run) < 3:
                    continue

                landmark_series = [
                    entry["landmarks"]
                    for entry in run
                ]

                repetitions = segment_reps(landmark_series)

                logger.warning(
                    "[RepCount] session=%s run=%s frames=%s reps=%s",
                    session.pk,
                    run_index,
                    len(run),
                    len(repetitions)
                )

                for rep in repetitions:
                    start_index = rep["start"]
                    bottom_index = rep["bottom"]
                    end_index = rep["end"]

                    if not (
                        0 <= start_index
                        <= bottom_index
                        <= end_index
                        < len(run)
                    ):
                        raise RuntimeError(
                            f"Invalid repetition range: {rep}"
                        )

                    rep_entries = run[start_index:end_index + 1]

                    if rep_entries:
                        segmented_rep_entries.append(rep_entries)

            if not segmented_rep_entries:
                raise RuntimeError(
                    "No complete squat repetitions were detected."
                )

            thresholds = session.exercise_variant.get_thresholds()

            prepared_assessments = []

            for rep_number, rep_entries in enumerate(
                segmented_rep_entries,
                start = 1
            ):
                rep_landmarks = [
                    entry["landmarks"]
                    for entry in rep_entries
                ]

                start_frame = rep_entries[0]["frame_index"]
                end_frame = rep_entries[-1]["frame_index"]

                analysis_result = analyze(
                    rep_landmarks,
                    thresholds
                )

                prepared_assessments.append({
                    "rep_number": rep_number,
                    "landmark_series": rep_landmarks,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "analysis_result": analysis_result
                })

            with transaction.atomic():
                RepAssessment.objects.filter(session=session).delete()

                for assessment in prepared_assessments:
                    RepAssessment.objects.create(
                        session=session,
                        rep_number=assessment["rep_number"],
                        landmark_series=assessment["landmark_series"],
                        start_frame=assessment["start_frame"],
                        end_frame=assessment["end_frame"],
                        analysis_result=assessment["analysis_result"]
                    )

            logger.warning(
                "[RepCount] session=%s saved_reps=%s",
                session.pk,
                len(prepared_assessments)
            )

            session.status = AssessmentSession.Status.COMPLETED

        except Exception as exc:
            logger.exception(
                "[RepCount] Processing failed for session=%s",
                session.pk
            )
            session.status = AssessmentSession.Status.FAILED
            session.error_message = str(exc)

        finally:
            session.processed_at = timezone.now()
            session.save(
                update_fields=[
                    "status",
                    "error_message",
                    "processed_at"
                ]
            )


class RepAssessmentViewSet(viewsets.ModelViewSet):
    serializer_class = RepAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RepAssessment.objects.filter(session__user=self.request.user)
