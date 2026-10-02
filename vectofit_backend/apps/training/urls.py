from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ModelRegistryViewSet, TrainingJobCreateView, TrainingJobViewSet

router = DefaultRouter()
router.register("jobs", TrainingJobViewSet, basename="training-job")
router.register("models", ModelRegistryViewSet, basename="model-registry")

urlpatterns = [
    path("jobs/", TrainingJobCreateView.as_view(), name="training-job-create"),
    path("", include(router.urls)),
]
