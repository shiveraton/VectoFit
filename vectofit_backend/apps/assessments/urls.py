from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .views import process_morphological_calibration

router = DefaultRouter()
router.register(
    r"sessions", views.AssessmentSessionViewSet, basename="assessment-session"
)
router.register(r"body-profiles", views.BodyProfileViewSet, basename="body-profile")
router.register(r"reps", views.RepAssessmentViewSet, basename="rep-assessment")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "calibrate/",
        process_morphological_calibration,
        name="morphological-calibration",
    ),
]
