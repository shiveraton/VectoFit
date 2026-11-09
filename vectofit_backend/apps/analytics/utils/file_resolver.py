import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path


class VideoResolutionError(Exception):
    pass


@contextmanager
def resolved_video_path(source, suffix=".mp4"):
    video_file = getattr(source, "video_file", source)
    if not video_file or not video_file.name:
        raise VideoResolutionError("No video file is attached.")
    try:
        native = video_file.path
    except (NotImplementedError, AttributeError, ValueError, OSError):
        native = None
    if native and os.path.isfile(native):
        yield native
        return
    with tempfile.TemporaryDirectory(prefix="vectofit_video_") as directory:
        path = Path(directory) / ("video" + (Path(video_file.name).suffix or suffix))
        try:
            with video_file.storage.open(video_file.name, "rb") as remote, path.open("wb") as local:
                shutil.copyfileobj(remote, local)
            if path.stat().st_size == 0:
                raise VideoResolutionError("The video file is empty.")
        except VideoResolutionError:
            raise
        except Exception as exc:
            raise VideoResolutionError("The video could not be read from storage.") from exc
        yield str(path)


def has_usable_video(dataset):
    try:
        return bool(dataset.video_file)
    except (AttributeError, ValueError, OSError):
        return False
