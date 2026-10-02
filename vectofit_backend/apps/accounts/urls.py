from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from .views import RegisterAPIView, LoginAPIView, ProfileViewSet, CurrentUserViewSet

router = DefaultRouter()
router.register(r'profile', ProfileViewSet, basename='profile')
router.register(r'me', CurrentUserViewSet, basename='me')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('register/', RegisterAPIView.as_view(), name='register'),
]