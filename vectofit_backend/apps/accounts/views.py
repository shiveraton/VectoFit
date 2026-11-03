from typing import ClassVar

from django.conf import settings
from django.db.models import Count
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.datasets.models import DatasetAnnotatorAssignment

from .models import Profile, User
from .roles import ANNOTATOR_GROUP
from .serializers import (
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)


class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if Profile.objects.filter(user=self.request.user).exists():
            raise ValidationError({"detail": "A profile already exists for this user."})

        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get", "patch"], url_path="current")
    def current(self, request):
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={"email": request.user.email},
        )

        if request.method == "PATCH":
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = self.get_serializer(profile)

        return Response(serializer.data)


class CurrentUserViewSet(viewsets.ViewSet):
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def list(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RegisterAPIView(APIView):
    permission_classes: ClassVar[list] = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not getattr(settings, "ANNOTATOR_SELF_REGISTRATION", True):
            return Response(
                {"detail": "Public annotator sign-up is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "message": "Account created.",
                "token": token.key,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AnnotatorDirectoryView(APIView):
    permission_classes: ClassVar[list] = [permissions.IsAdminUser]

    def get(self, request):
        users = list(
            User.objects.filter(
                groups__name=ANNOTATOR_GROUP,
                is_staff=False,
            )
            .order_by("username")
            .distinct()
        )
        assigned = dict(
            DatasetAnnotatorAssignment.objects.filter(
                annotator__in=users, is_active=True
            )
            .values("annotator")
            .annotate(total=Count("id"))
            .values_list("annotator", "total")
        )
        return Response(
            [
                {
                    "id": user.pk,
                    "username": user.username,
                    "email": user.email,
                    "date_joined": user.date_joined,
                    "is_active": user.is_active,
                    "assigned_datasets": assigned.get(user.pk, 0),
                }
                for user in users
            ]
        )


class LoginAPIView(APIView):
    permission_classes: ClassVar[list] = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
