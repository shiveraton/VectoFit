from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sessions', views.AssessmentSessionViewSet, basename='assessment-session')
router.register(r'body-profiles', views.BodyProfileViewSet, basename='body-profile')
router.register(r'reps', views.RepAssessmentViewSet, basename='rep-assessment')

urlpatterns = [
    path('', include(router.urls))
]