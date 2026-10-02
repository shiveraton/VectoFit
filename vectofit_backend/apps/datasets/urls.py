from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import DatasetSampleViewSet, DatasetViewSet

router = DefaultRouter()

router.register(r'', DatasetViewSet, basename='dataset')
router.register(r'dataset-samples', DatasetSampleViewSet, basename='datasetsample')

urlpatterns = [
    path('', include(router.urls)),
]