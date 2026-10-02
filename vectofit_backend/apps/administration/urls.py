from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'ml-model', views.MLModelViewSet, basename='ml-model')
router.register(r'training-job', views.TrainingJobViewSet, basename='training-job')
router.register(r'administration', views.AdministrationViewSet, basename='administration')

urlpatterns = [
    path('', include(router.urls)),
]