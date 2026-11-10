from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.roles import is_validator
from apps.datasets.services.media import protected_file_response
from .models import ValidationAnnotation, ValidationSample
from .serializers import ValidationAnnotationSerializer

MEDIA_SALT = "vectofit.validation-media"


class IsValidator(BasePermission):
    def has_permission(self, request, view):
        return is_validator(request.user)


@method_decorator(never_cache, name="dispatch")
class ValidationSampleView(APIView):
    permission_classes = [IsValidator]

    def get(self, request):
        rows = ValidationSample.objects.select_related("repetition__rep_assessment")
        result = []
        for row in rows:
            rep = row.repetition.rep_assessment
            token = signing.dumps({"sample_id": row.pk, "user_id": request.user.pk}, salt=MEDIA_SALT)
            path = reverse("validation-media", kwargs={"sample_id": row.pk})
            result.append({"repetition_id": row.repetition_id, "assessment_rep_id": rep.pk,
                           "rep_number": rep.rep_number, "start_frame": rep.start_frame,
                           "end_frame": rep.end_frame, "protocol_version": row.protocol_version,
                           "video_url": request.build_absolute_uri(f"{path}?token={token}")})
        return Response(result)


@method_decorator(never_cache, name="dispatch")
class ValidationRatingView(APIView):
    permission_classes = [IsValidator]

    def get(self, request, repetition_id):
        get_object_or_404(ValidationSample, repetition_id=repetition_id)
        row = get_object_or_404(ValidationAnnotation, repetition_id=repetition_id, validator=request.user)
        return Response(ValidationAnnotationSerializer(row).data)

    @transaction.atomic
    def put(self, request, repetition_id):
        sample = get_object_or_404(ValidationSample.objects.select_for_update(), repetition_id=repetition_id)
        row = ValidationAnnotation.objects.filter(repetition_id=repetition_id, validator=request.user).first()
        serializer = ValidationAnnotationSerializer(row, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(repetition_id=repetition_id, validator=request.user,
                        protocol_version=sample.protocol_version)
        return Response(serializer.data, status=200 if row else 201)


@method_decorator(never_cache, name="dispatch")
class ValidationMediaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, sample_id):
        try:
            payload = signing.loads(request.query_params.get("token", ""), salt=MEDIA_SALT, max_age=900)
        except signing.BadSignature:
            return HttpResponse(status=404)
        if not isinstance(payload, dict) or payload.get("sample_id") != sample_id:
            return HttpResponse(status=404)
        user = get_user_model().objects.filter(pk=payload.get("user_id"), is_active=True).first()
        if not is_validator(user):
            return HttpResponse(status=404)
        sample = get_object_or_404(ValidationSample.objects.select_related(
            "repetition__dataset_video", "repetition__dataset"), pk=sample_id)
        repetition = sample.repetition
        media = repetition.dataset_video.video_file if repetition.dataset_video_id else repetition.dataset.video_file
        return protected_file_response(request, media, filename="validation.mp4")
