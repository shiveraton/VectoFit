import mimetypes
import re
from django.contrib.auth import get_user_model
from django.core import signing
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.roles import is_annotator

from .models import Dataset, DatasetAnnotatorAssignment, DatasetVideo

MEDIA_SIGNING_SALT = "vectofit.dataset-media"
MEDIA_URL_MAX_AGE_SECONDS = 15 * 60


def signed_dataset_media_url(request, kind, object_id, dataset):
    if request is None or not request.user.is_authenticated:
        return None

    user = request.user
    if (
        not user.is_staff
        and not DatasetAnnotatorAssignment.objects.filter(
            dataset=dataset,
            annotator=user,
            is_active=True,
        ).exists()
    ):
        return None

    token = signing.dumps(
        {"kind": kind, "object_id": object_id, "user_id": user.pk},
        salt=MEDIA_SIGNING_SALT,
    )
    path = reverse(
        "dataset-media",
        kwargs={"kind": kind, "object_id": object_id},
    )
    return request.build_absolute_uri(f"{path}?token={token}")


class DatasetMediaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, kind, object_id):
        token = request.query_params.get("token", "")
        try:
            payload = signing.loads(
                token,
                salt=MEDIA_SIGNING_SALT,
                max_age=MEDIA_URL_MAX_AGE_SECONDS,
            )
        except signing.BadSignature:
            return HttpResponse(status=404)

        if not isinstance(payload, dict):
            return HttpResponse(status=404)
        if payload.get("kind") != kind or payload.get("object_id") != object_id:
            return HttpResponse(status=404)

        User = get_user_model()
        user = User.objects.filter(
            pk=payload.get("user_id"),
            is_active=True,
        ).first()
        if user is None:
            return HttpResponse(status=404)

        if kind == "dataset":
            dataset = get_object_or_404(Dataset, pk=object_id)
            media_file = dataset.video_file
        elif kind == "dataset-video":
            video = get_object_or_404(
                DatasetVideo.objects.select_related("dataset"),
                pk=object_id,
            )
            dataset = video.dataset
            media_file = video.video_file
        else:
            return HttpResponse(status=404)

        if not user.is_staff:
            has_access = (
                is_annotator(user)
                and DatasetAnnotatorAssignment.objects.filter(
                    dataset=dataset,
                    annotator=user,
                    is_active=True,
                ).exists()
            )
            if not has_access:
                return HttpResponse(status=404)

        if not media_file:
            return HttpResponse(status=404)

        file_handle = media_file.open("rb")
        file_size = media_file.size
        content_type = (
            mimetypes.guess_type(media_file.name)[0] or "application/octet-stream"
        )
        range_header = request.headers.get("Range")

        if not range_header:
            response = FileResponse(file_handle, content_type=content_type)
            response["Accept-Ranges"] = "bytes"
            response["Cache-Control"] = "private, no-store"
            return response

        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if match is None or file_size == 0:
            file_handle.close()
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{file_size}"
            return response

        first, last = match.groups()
        if first:
            start = int(first)
            end = int(last) if last else file_size - 1
        else:
            suffix_length = int(last or 0)
            start = max(file_size - suffix_length, 0)
            end = file_size - 1

        if start >= file_size or end < start:
            file_handle.close()
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{file_size}"
            return response

        end = min(end, file_size - 1)
        file_handle.seek(start)
        remaining = end - start + 1

        def stream_range():
            nonlocal remaining
            try:
                while remaining:
                    chunk = file_handle.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
            finally:
                file_handle.close()

        response = StreamingHttpResponse(
            stream_range(),
            status=206,
            content_type=content_type,
        )
        response["Accept-Ranges"] = "bytes"
        response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        response["Content-Length"] = str(end - start + 1)
        response["Cache-Control"] = "private, no-store"
        return response
