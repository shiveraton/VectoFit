from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActivityLogViewSet, AdminUserViewSet, CurrentUserViewSet, LoginAPIView, ProfileViewSet, RegisterAPIView

router = DefaultRouter()
router.register(r"users", AdminUserViewSet, basename="admin-users")
router.register(r"activity-logs", ActivityLogViewSet, basename="activity-logs")
router.register(r"profile", ProfileViewSet, basename="profile")
router.register(r"me", CurrentUserViewSet, basename="me")

urlpatterns = [
    path("", include(router.urls)),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("register/", RegisterAPIView.as_view(), name="register"),
]
