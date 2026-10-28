from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import(
    DatasetSampleViewSet, 
    DatasetViewSet,
    DatasetVideoViewSet,
    DatasetImportPreviewView,
    DatasetBulkImportView,
    ParticipantViewSet,
    ViewAngleViewSet,
)

router = DefaultRouter()

router.register(r'', DatasetViewSet, basename='dataset')
router.register(r'dataset-samples', DatasetSampleViewSet, basename='dataset-sample')
router.register(r'dataset-videos', DatasetVideoViewSet, basename='dataset-video')
router.register(r'participant', ParticipantViewSet, basename='participant')
router.register(r'view-angle', ViewAngleViewSet, basename='view-angle')
router.register(r'retry', DatasetViewSet, basename='retry')

urlpatterns = [
    path('', include(router.urls)),
    path("import/preview/", DatasetImportPreviewView.as_view(), name="dataset-import-preview"),
    path("import/", DatasetBulkImportView.as_view(), name="dataset_bulk_import")
]