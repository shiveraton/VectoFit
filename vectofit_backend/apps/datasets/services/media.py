import mimetypes
import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.utils.http import content_disposition_header


class FileRange:
    def __init__(self, file, length):
        self.file = file
        self.remaining = length

    def __iter__(self):
        return self

    def __next__(self):
        if self.remaining <= 0:
            self.close()
            raise StopIteration
        try:
            chunk = self.file.read(min(64 * 1024, self.remaining))
        except Exception:
            self.close()
            raise
        if not chunk:
            self.close()
            raise StopIteration
        self.remaining -= len(chunk)
        return chunk

    def close(self):
        self.file.close()


def byte_range(header, size):
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if match is None or size == 0:
        return None
    first, last = match.groups()
    if max(len(first), len(last)) > 20:
        return None
    if first:
        start = int(first)
        end = int(last) if last else size - 1
    else:
        suffix = int(last or 0)
        if suffix <= 0:
            return None
        start, end = max(size - suffix, 0), size - 1
    if start >= size or end < start:
        return None
    return start, min(end, size - 1)


def protected_file_response(request, media_file, filename=None):
    if not media_file:
        raise Http404
    file = None
    try:
        try:
            local_path = media_file.path
        except NotImplementedError:
            local_path = None
        if local_path is not None and not Path(local_path).resolve().is_relative_to(
            Path(settings.MEDIA_ROOT).resolve()
        ):
            raise Http404
        file = media_file.open("rb")
        size = media_file.size
        name = filename or Path(media_file.name).name
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        header = (
            request.headers.get("Range")
            if request.method == "GET" and not request.headers.get("If-Range")
            else None
        )
        if header:
            span = byte_range(header, size)
            if span is None:
                file.close()
                response = HttpResponse(status=416)
                response["Content-Range"] = f"bytes */{size}"
                response["Content-Length"] = "0"
            else:
                start, end = span
                file.seek(start)
                response = StreamingHttpResponse(
                    FileRange(file, end - start + 1),
                    status=206,
                    content_type=content_type,
                )
                response["Content-Range"] = f"bytes {start}-{end}/{size}"
                response["Content-Length"] = str(end - start + 1)
        elif request.method == "HEAD":
            file.close()
            response = HttpResponse(content_type=content_type)
            response["Content-Length"] = str(size)
        else:
            response = FileResponse(file, content_type=content_type)
            response["Content-Length"] = str(size)
    except (OSError, ValueError, SuspiciousFileOperation):
        if file is not None:
            file.close()
        raise Http404 from None
    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Disposition"] = content_disposition_header(False, name)
    return response
