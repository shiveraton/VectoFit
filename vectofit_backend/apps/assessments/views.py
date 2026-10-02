from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.parsers import MultiPartParser, FormParser

from .models import BodyProfile, RepAssessment, AssessmentSession
from .serializers import (
    BodyProfileSerializer, 
    RepAssessmentSerializer, 
    AssessmentSessionSerializer, 
    AssessmentSessionDetailSerializer,
)

from .services.pose_estimator import PoseEstimator
from .services.video_processor import VideoProcessor

class BodyProfileViewSet(viewsets.ModelViewSet):
    serializer_class = BodyProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BodyProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AssessmentSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [FormParser, MultiPartParser]

    def get_queryset(self):
        return AssessmentSession.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AssessmentSessionDetailSerializer
        return AssessmentSessionSerializer

    def perform_create(self, serializer):
        session = serializer.save(user=self.request.user)
        self._process_session(session)

    def _process_session(self, session):
        session.status = AssessmentSession.Status.PROCESSING
        session.save(update_fields=["status"])

        try:
            processor = VideoProcessor(session.video_file.path)
            frames = processor.extract_frames() # 30 fps downsampled, 1280*720

            estimator = PoseEstimator()
            landmark_series = []

            for frame in frames:
                results = estimator.estimate_pose(frame)
                landmark_positions = estimator.get_landmark_positions(frame, results)
                named_landmarks = estimator.get_named_landmarks(landmark_positions)
                landmark_series.append(named_landmarks)

            RepAssessment.objects.create(
                session = session,
                rep_number = 1,
                landmark_series=landmark_series,
            )

            session.status = AssessmentSession.Status.COMPLETED

        except Exception as exc:
            session.status = AssessmentSession.Status.FAILED
            session.error_message = str(exc)
        finally:
            session.processed_at = timezone.now()
            session.save(update_fields = ["status", "error_message", "processed_at"])

class RepAssessmentViewSet(viewsets.ModelViewSet):
    serializer_class = RepAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RepAssessment.objects.filter(session__user=self.request.user)