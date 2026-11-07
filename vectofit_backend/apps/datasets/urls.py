from .assignment_views import AnnotatorPickerView, AssignmentListView, AssignmentDetailView, AssignmentEventListView
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .media_views import DatasetMediaView
from .views import (
    DatasetBulkImportView,
    DatasetImportPreviewView,
    DatasetSampleViewSet,
    DatasetVideoViewSet,
    DatasetViewSet,
    ParticipantViewSet,
    ViewAngleViewSet,
)
from .views import AnnotationDatasetListView, AnnotationPoolView

router = DefaultRouter()

router.register(r"", DatasetViewSet, basename="dataset")
router.register(r"dataset-samples", DatasetSampleViewSet, basename="dataset-sample")
router.register(r"dataset-videos", DatasetVideoViewSet, basename="dataset-video")
router.register(r"participant", ParticipantViewSet, basename="participant")
router.register(r"view-angle", ViewAngleViewSet, basename="view-angle")
router.register(r"retry", DatasetViewSet, basename="retry")

urlpatterns = [
    path("annotators/", AnnotatorPickerView.as_view(), name="dataset-annotators"),
    path("<int:dataset_id>/assignments/", AssignmentListView.as_view(), name="dataset-assignments"),
    path("<int:dataset_id>/assignments/events/", AssignmentEventListView.as_view(), name="dataset-assignment-events"),
    path("<int:dataset_id>/assignments/<int:annotator_id>/", AssignmentDetailView.as_view(), name="dataset-assignment-detail"),
    path(
        "media/<str:kind>/<int:object_id>/",
        DatasetMediaView.as_view(),
        name="dataset-media",
    ),
    path("", include(router.urls)),
    path(
        "import/preview/",
        DatasetImportPreviewView.as_view(),
        name="dataset-import-preview",
    ),
    path("import/", DatasetBulkImportView.as_view(), name="dataset_bulk_import"),
    path(
        "annotation-datasets/",
        AnnotationDatasetListView.as_view(),
        name="annotation-dataset-list",
    ),
    path(
        "annotation-pool/",
        AnnotationPoolView.as_view(),
        name="annotation-pool",
    ),
]
