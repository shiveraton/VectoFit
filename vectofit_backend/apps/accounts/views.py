from typing import ClassVar

from django.db import transaction
from django.db.models import Q
from django.contrib.auth.models import User
from rest_framework.pagination import PageNumberPagination

from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivityLog, Profile
from .permissions import IsAccountAdministrator
from .serializers import (
    ActivityLogSerializer,
    AdminUserSerializer,
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

    @transaction.atomic
    def partial_update(self, request, pk=None):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changed_fields = [
            field for field, value in serializer.validated_data.items()
            if getattr(request.user, field) != value
        ]
        serializer.save()
        if changed_fields:
            ActivityLog.objects.create(
                actor=request.user,
                actor_username=request.user.username,
                action=ActivityLog.Action.ACCOUNT_UPDATED,
                details="Updated " + ", ".join(sorted(changed_fields)),
            )
        return Response(serializer.data)


class RegisterAPIView(APIView):
    permission_classes: ClassVar[list] = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            ActivityLog.objects.create(
                actor=user,
                actor_username=user.username,
                action=ActivityLog.Action.REGISTERED,
            )

            return Response(
                {"message": "User registered successfully."},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    permission_classes: ClassVar[list] = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            token, created = Token.objects.get_or_create(user=user)
            ActivityLog.objects.create(
                actor=user,
                actor_username=user.username,
                action=ActivityLog.Action.SIGN_IN,
            )
            return Response({"token": token.key}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class AdministrationPagination(PageNumberPagination):
    page_size = 25


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = [IsAccountAdministrator]
    pagination_class = AdministrationPagination
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        users = User.objects.select_related("profile").order_by("username", "id")
        search = self.request.query_params.get("search", "").strip()
        if search:
            users = users.filter(Q(username__icontains=search) | Q(email__icontains=search))
        return users


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAccountAdministrator]
    pagination_class = AdministrationPagination
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        logs = ActivityLog.objects.all()
        search = self.request.query_params.get("search", "").strip()
        if search:
            logs = logs.filter(Q(actor_username__icontains=search) | Q(details__icontains=search))
        action = self.request.query_params.get("action", "")
        if action:
            logs = logs.filter(action=action)
        return logs
