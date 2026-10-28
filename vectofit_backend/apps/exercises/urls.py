from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

router.register(r"variants", views.ExerciseVariantViewSet, basename="exercise-variant")

urlpatterns = [
    path("", include(router.urls)),
]
