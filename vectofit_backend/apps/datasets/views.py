from rest_framework import permissions, viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Dataset, DatasetSample
from .serializers import DatasetSerializer, DatasetSampleSerializer
from .services.tasks import process_dataset_video_task
from apps.assessments.services.video_processor import VideoProcessor
from apps.assessments.services.pose_estimator import PoseEstimator

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all().order_by('-created_at')
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAdminUser]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def perform_create(self, serializer):
        dataset = serializer.save(status='PENDING')
        process_dataset_video_task.delay(dataset.id)

    def _process_dataset_video(self, dataset):
        dataset.status = 'PROCESSING'
        dataset.save(update_fields=['status'])

        try:
            if hasattr(dataset, 'video_file') and dataset.video_file:
                processor = VideoProcessor(dataset.video_file.path)
                frames = processor.extract_frames

                estimator = PoseEstimator()
                landmark_series = []

                for frame in frames:
                    results = estimator.estimate_pose(frame)
                    landmark_positions = estimator.get_landmark_positions(frame, results)
                    named_landmarks = estimator.get_named_landmarks(landmark_positions)
                    landmark_series.append(named_landmarks)

                DatasetSample.objects.create(
                    dataset=dataset,
                    landmark_series=landmark_series,
                    total_frames=len(landmark_series)
                )

                dataset.status = 'READY'
        except Exception as exc:
            dataset.status = 'FAILED'
            dataset.error_message = str(exc)
        finally:
            dataset.save(update_fields=['status', 'error_message'])

    def get_serializer_context(self):
        return {'request': self.request}

class DatasetSampleViewSet(viewsets.ModelViewSet):
    queryset = DatasetSample.objects.all()
    serializer_class = DatasetSampleSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()
        dataset_id = self.request.query_params.get('dataset')
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        return queryset
    