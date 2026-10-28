"""Storage-agnostic resolution of uploaded video files to local disk paths.

Why this exists
---------------
``FieldFile.path`` only works for storage backends that keep files on the local
filesystem (FileSystemStorage). With Supabase/S3-style backends, ``.path``
either raises ``NotImplementedError`` or returns a URL, neither of which
OpenCV can open. Training must not depend on the storage backend in use, so
everything that needs a real file on disk goes through this module.

The resolver never surfaces storage credentials or bucket internals to callers
or to the API layer -- it returns a local path and nothing else.
"""

import os
import shutil
import tempfile
from contextlib import contextmanager

from django.core.files.storage import default_storage

from apps.datasets.models import Dataset


class VideoResolutionError(Exception):
    """Raised when a Dataset's video cannot be turned into a local file."""


def _try_native_path(dataset):
    """Return the backend-provided local path, or None if it is not usable.

    Many storages raise instead of returning a sentinel, so every failure mode
    is caught and treated as "no local path available".
    """
    try:
        video_file = dataset.video_file
    except (AttributeError, ValueError, OSError):
        return None

    if not video_file:
        return None

    try:
        path = video_file.path
    except (NotImplementedError, AttributeError, ValueError, OSError):
        return None

    if not path or not isinstance(path, str):
        return None

    return path if os.path.isfile(path) else None


def _materialize_to_temp(dataset, suffix):
    """Stream the file through the storage API into a temporary local file."""
    try:
        name = dataset.video_file.name
    except Exception as exc:
        raise VideoResolutionError(
            f"Dataset {dataset.pk} has no readable video file reference."
        ) from exc

    if not name:
        raise VideoResolutionError(f"Dataset {dataset.pk} has no video file attached.")

    tmp_dir = tempfile.mkdtemp(prefix="vectofit_video_")
    ext = os.path.splitext(name)[1] or suffix or ".mp4"
    tmp_path = os.path.join(tmp_dir, f"dataset_{dataset.pk}{ext}")

    try:
        with default_storage.open(name, "rb") as remote:
            with open(tmp_path, "wb") as local:
                shutil.copyfileobj(remote, local)
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise VideoResolutionError(
            f"Dataset {dataset.pk} video could not be downloaded from storage "
            f"({name!r}): {exc}"
        ) from exc

    if os.path.getsize(tmp_path) == 0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise VideoResolutionError(
            f"Dataset {dataset.pk} video downloaded from storage is empty."
        )

    return tmp_dir, tmp_path


@contextmanager
def resolved_video_path(dataset, suffix=".mp4"):
    """Yield a local filesystem path for ``dataset``'s video.

    Uses the storage backend's own local path when one exists, otherwise
    materializes a temporary copy and deletes it (with its directory) on exit.

    The yielded path is only guaranteed to be valid inside the ``with`` block.
    """
    if not isinstance(dataset, Dataset):
        raise TypeError("resolved_video_path expects a Dataset instance.")

    native = _try_native_path(dataset)
    if native is not None:
        # Owned by the storage backend -- do not delete it.
        yield native
        return

    tmp_dir, tmp_path = _materialize_to_temp(dataset, suffix)
    try:
        yield tmp_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def has_usable_video(dataset):
    """Cheap pre-check: does this dataset have a video attached at all?"""
    try:
        return bool(dataset.video_file)
    except (AttributeError, ValueError, OSError):
        return False
