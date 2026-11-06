import mimetypes
from pathlib import Path
from urllib.parse import quote

import cv2
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import Http404, HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Profile
from apps.datasets.models import Dataset, DatasetSample, KneeAnnotation
from apps.datasets.serializers import KneeAnnotationField
from apps.datasets.services.annotation import latest_annotation
from apps.datasets.services.knee_label import knee_target


class IsPublicAnnotator(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and user.is_active
            and not user.is_staff
            and not user.is_superuser
            and getattr(getattr(user, "profile", None), "is_annotator", False)
        )


@method_decorator(never_cache, name="dispatch")
class PublicView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsPublicAnnotator,)


def identity(user):
    return {"id": user.pk, "username": user.username, "is_annotator": True}


class CsrfView(PublicView):
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class EnrollmentSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]+$", max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=256
    )
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)
    invitation_code = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=256
    )

    def validate(self, data):
        secret = settings.ANNOTATOR_INVITATION_CODE
        if not secret or not constant_time_compare(data["invitation_code"], secret):
            raise serializers.ValidationError("Invalid invitation code.")
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        user = get_user_model()(username=data["username"], email=data["email"])
        try:
            validate_password(data["password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return data


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(PublicView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = EnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            with transaction.atomic():
                user = get_user_model().objects.create_user(
                    username=data["username"],
                    email=data["email"],
                    password=data["password"],
                    is_staff=False,
                    is_superuser=False,
                )
                Profile.objects.update_or_create(
                    user=user, defaults={"is_annotator": True, "email": data["email"]}
                )
        except IntegrityError:
            raise serializers.ValidationError("Username is unavailable.")
        return Response({"detail": "Account created. Please sign in."}, status=201)


class CredentialsSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(
        max_length=256, trim_whitespace=False, write_only=True
    )


@method_decorator(csrf_protect, name="dispatch")
class LoginView(PublicView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = CredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        if (
            not user
            or user.is_staff
            or user.is_superuser
            or not getattr(getattr(user, "profile", None), "is_annotator", False)
        ):
            return Response({"detail": "Invalid annotator credentials."}, status=403)
        login(request, user)
        return Response({**identity(user), "csrfToken": get_token(request)})


class MeView(PublicView):
    def get(self, request):
        return Response(identity(request.user))


class LogoutView(PublicView):
    def post(self, request):
        logout(request)
        return Response({"detail": "Signed out."})


def eligible_samples():
    return DatasetSample.objects.filter(
        dataset__status="READY",
        dataset_video__status="READY",
        dataset_video__requires_manual_review=True,
        dataset_video__dataset_id=F("dataset_id"),
    ).select_related(
        "dataset",
        "rep_assessment",
        "dataset_video__participant",
        "dataset_video__view_angle",
    )


def sample_data(sample, user, fps=None):
    record = latest_annotation(sample, user)
    annotation = record.annotation if record else None
    rep, video = sample.rep_assessment, sample.dataset_video
    return {
        "id": sample.pk,
        "dataset": sample.dataset_id,
        "dataset_video": {
            "id": video.pk,
            "video_url": f"/api/annotator/videos/{video.pk}/",
            "participant_code": video.participant.participant_code,
            "view_angle_name": video.view_angle.angle_variant,
        },
        "video_fps": fps,
        "knee_annotation": annotation,
        "target_label": knee_target(annotation) if annotation else None,
        "rep_assessment": {
            "id": rep.pk,
            "rep_number": rep.rep_number,
            "start_frame": rep.start_frame,
            "end_frame": rep.end_frame,
        },
    }


class DatasetListView(PublicView):
    def get(self, request):
        ids = eligible_samples().values("dataset_id")
        return Response(
            [
                {"id": dataset.pk, "name": f"Dataset {dataset.pk}"}
                for dataset in Dataset.objects.filter(pk__in=ids).order_by("pk")
            ]
        )


class SessionView(PublicView):
    def get(self, request, dataset_id):
        samples = list(
            eligible_samples()
            .filter(dataset_id=dataset_id)
            .order_by("dataset_video_id", "rep_assessment__rep_number", "id")
        )
        if not samples:
            raise Http404
        fps = {}
        for sample in samples:
            video = sample.dataset_video
            if video.pk not in fps:
                cap = cv2.VideoCapture(video.video_file.path)
                try:
                    fps[video.pk] = float(cap.get(cv2.CAP_PROP_FPS) or 0)
                finally:
                    cap.release()
        rows = [
            sample_data(sample, request.user, fps[sample.dataset_video_id])
            for sample in samples
        ]
        return Response(
            {
                "dataset": {
                    "id": dataset_id,
                    "name": f"Dataset {dataset_id}",
                    "video_url": None,
                    "sample_count": len(rows),
                    "labelled_sample_count": sum(
                        row["knee_annotation"] is not None for row in rows
                    ),
                },
                "fps": 0,
                "samples": rows,
            }
        )


class PublicKneeAnnotationField(KneeAnnotationField):
    def to_internal_value(self, value):
        try:
            return super().to_internal_value(value)
        except (TypeError, KeyError) as exc:
            raise serializers.ValidationError(
                "Invalid knee annotation values."
            ) from exc


class RatingSerializer(serializers.Serializer):
    knee_annotation = PublicKneeAnnotationField(allow_null=True)

    def validate_knee_annotation(self, value):
        if value is not None and any(
            value[side]["grade"] is None for side in ("left", "right")
        ):
            raise serializers.ValidationError("Assess both knees before saving.")
        if value is not None and len(value["notes"]) > 4000:
            raise serializers.ValidationError("Notes must be at most 4000 characters.")
        return value


class RatingView(PublicView):
    def patch(self, request, sample_id):
        serializer = RatingSerializer(data=request.data)
        if not isinstance(request.data, dict) or set(request.data) != {
            "knee_annotation"
        }:
            raise serializers.ValidationError("Only knee_annotation may be changed.")
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            sample = get_object_or_404(
                eligible_samples().select_for_update(of=("self",)), pk=sample_id
            )
            # Append a tombstone when clearing; preserve every other rater and history.
            KneeAnnotation.objects.create(
                sample=sample,
                annotator=request.user,
                annotation=serializer.validated_data["knee_annotation"],
            )
        return Response(sample_data(sample, request.user))


class VideoView(PublicView):
    def get(self, request, video_id):
        sample = eligible_samples().filter(dataset_video_id=video_id).first()
        if sample is None:
            raise Http404
        file = sample.dataset_video.video_file
        media_root = Path(settings.MEDIA_ROOT).resolve()
        path = Path(file.path).resolve()
        if not path.is_relative_to(media_root) or not path.is_file():
            raise Http404
        response = HttpResponse(
            content_type=mimetypes.guess_type(path.name)[0]
            or "application/octet-stream"
        )
        response["X-Accel-Redirect"] = "/_protected_media/" + quote(
            path.relative_to(media_root).as_posix(), safe="/"
        )
        response["Content-Disposition"] = (
            'inline; filename="review-video' + path.suffix.lower() + '"'
        )
        return response
