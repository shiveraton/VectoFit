from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.analytics import views

router = DefaultRouter()
router.register(r'daily-trend', views.DailyActivityPointViewSet, basename='daily-trend')
router.register(r'weekly-trend', views.WeeklyTrendViewSet, basename='weekly-trend')
router.register(r'trend-series', views.TrendSeriesViewSet, basename='trend-series')
router.register(r'variant-trend', views.VariantTrendViewSet, basename='variant-trend')

urlpatterns = [
    path('', include(router.urls))
]