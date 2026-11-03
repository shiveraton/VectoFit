from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ExperimentReadinessView,
    ExperimentResultsView,
    ModelRegistryViewSet,
    ModelStateView,
    TrainingJobCreateView,
    TrainingJobViewSet,
)

router = DefaultRouter()

router.register("jobs", TrainingJobViewSet, basename="training-job")
router.register("models", ModelRegistryViewSet, basename="model-registry")

urlpatterns = [
    path("jobs/create/", TrainingJobCreateView.as_view(), name="training-job-create"),
    path("models/<int:pk>/state/", ModelStateView.as_view(), name="model-state"),
    path(
        "experiments/readiness/",
        ExperimentReadinessView.as_view(),
        name="experiment-readiness",
    ),
    path(
        "experiments/results/",
        ExperimentResultsView.as_view(),
        name="experiment-results",
    ),
    path("", include(router.urls)),
]
