import json
import logging
import re
import uuid
import zipfile
from datetime import timedelta
from pathlib import Path, PurePosixPath

logger = logging.getLogger(__name__)
UPLOAD_CHUNK_SIZE = 4 * 1024 * 1024

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

STAGING_DIR = Path(settings.MEDIA_ROOT) / "dataset_import_staging"

MAX_ARCHIVE_BYTES = getattr(settings, "DATASET_IMPORT_MAX_ARCHIVE_BYTES", 4 * 1024**3)

MAX_UNCOMPRESSED_BYTES = getattr(
    settings, "DATASET_IMPORT_MAX_UNCOMPRESSED_BYTES", 20 * 1024**3
)

MAX_ARCHIVE_ENTRIES = 1000
PREVIEW_TTL = timedelta(hours=1)
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi"}

GOOD_TOKENS = {"good", "correct", "proper", "pass", "acceptable"}
BAD_TOKENS = {"bad", "incorrect", "poor", "fail", "faulty"}

LABEL_TOKENS = GOOD_TOKENS | BAD_TOKENS

ANGLE_TOKENS = {
    "diagonal",
    "frontal",
    "front",
    "sagittal",
    "side",
    "45",
    "deg",
    "degree",
    "degrees",
}

METADATA_TOKENS = (
    LABEL_TOKENS
    | ANGLE_TOKENS
    | {
        "squat",
        "bodyweight",
        "bw",
        "form",
        "view",
        "video",
        "recording",
        "participant",
        "subject",
        "sub",
    }
)

ANGLE_NAMES = ("diagonal", "frontal", "sagittal")


def empty_manifest():
    return {
        "file_count": 0,
        "participant_count": 0,
        "by_angle": {name: 0 for name in ANGLE_NAMES},
        "by_label": {"good": 0, "bad": 0},
        "files": [],
        "warnings": [],
        "errors": [],
        "ignored_file_count": 0,
    }


def _tokens(value):
    return re.findall(r"[a-z0-9]+", value.lower())


def _angle_for_component(component):
    stem = PurePosixPath(component).stem
    tokens = set(_tokens(stem))
    compact = re.sub(r"[^a-z0-9]", "", stem.lower())

    if (
        "diagonal" in tokens
        or compact in {"45", "45deg", "45degree", "45degrees"}
        or ("45" in tokens and bool(tokens & {"deg", "degree", "degrees"}))
    ):
        return "diagonal"

    if tokens & {"frontal", "front"}:
        return "frontal"

    if tokens & {"sagittal", "side"}:
        return "sagittal"

    return None


def _labels_for_component(component):
    tokens = set(_tokens(PurePosixPath(component).stem))
    labels = set()

    if tokens & GOOD_TOKENS:
        labels.add(True)

    if tokens & BAD_TOKENS:
        labels.add(False)

    return labels


def _normalize_participant_code(value):
    value = value.strip()

    numeric_match = re.fullmatch(
        r"(?i)(?:participant|subject|sub|p)?[\s_-]*0*(\d{1,3})",
        value,
    )

    if numeric_match:
        return f"P{int(numeric_match.group(1)):02d}"

    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value)
    value = value.strip("_-").upper()

    if len(value) > 32:
        return ""

    return value


def _participant_from_path(parts):
    participant_folder_pattern = re.compile(
        r"(?i)^(?:participant|subject|sub|p)?[\s_-]*0*\d{1,3}$"
    )

    for part in reversed(parts[:-1]):
        if participant_folder_pattern.fullmatch(part):
            code = _normalize_participant_code(part)
            if code:
                return code

    stem = PurePosixPath(parts[-1]).stem
    tokens = _tokens(stem)

    remaining = [token for token in tokens if token not in METADATA_TOKENS]

    if (
        len(remaining) >= 2
        and remaining[0] in {"participant", "subject", "sub"}
        and remaining[1].isdigit()
    ):
        return _normalize_participant_code(f"P{remaining[1]}")

    return _normalize_participant_code("_".join(remaining))


def inspect_archive(archive_path):
    result = empty_manifest()
    seen_paths = set()

    try:
        archive = zipfile.ZipFile(archive_path, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        result["errors"].append(f"Cannot read ZIP archive: {exc}")
        return result

    with archive:
        archive_entries = archive.infolist()

        if len(archive_entries) > MAX_ARCHIVE_ENTRIES:
            result["errors"].append("The archive contains way too many entries.")
            return result

        total_uncompressed = 0
        valid_entries = []

        for info in archive_entries:
            total_uncompressed += info.file_size

            if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                result["errors"].append(
                    "The archive exceeds the configured uncompressed-size limit."
                )
                break

            if info.is_dir():
                continue

            raw_path = info.filename

            if (
                raw_path.startswith(("/", "\\"))
                or "\\" in raw_path
                or ".." in PurePosixPath(raw_path).parts
            ):
                result["errors"].append(f"Unsafe archive path: {raw_path}")
                continue

            path = PurePosixPath(raw_path)

            if path.suffix.lower() not in VIDEO_SUFFIXES:
                result["ignored_file_count"] += 1
                continue

            if raw_path in seen_paths:
                result["errors"].append(f"Duplicate archive entry: {raw_path}")
                continue

            seen_paths.add(raw_path)

            if len(raw_path) > 255:
                result["errors"].append(f"Archive path is too long: {raw_path}")
                continue

            labels = set()
            angles = set()

            for component in path.parts:
                labels.update(_labels_for_component(component))

                angle = _angle_for_component(component)
                if angle:
                    angles.add(angle)

            if len(labels) != 1:
                result["errors"].append(
                    f"{raw_path}: expected exactly one good/bad "
                    "label in the folder structure or filename."
                )
                continue

            if len(angles) != 1:
                result["errors"].append(
                    f"{raw_path}: expected exactly one view angle "
                    "(diagonal, frontal, or sagittal)."
                )
                continue

            participant_code = _participant_from_path(list(path.parts))

            if not participant_code:
                result["errors"].append(
                    f"{raw_path}: could not identify a participant. "
                    "Name the file using a participant code such as P01.mp4."
                )
                continue

            label = next(iter(labels))
            angle = next(iter(angles))

            valid_entries.append(
                {
                    "archive_path": raw_path,
                    "filename": path.name,
                    "participant_code": participant_code,
                    "view_angle": angle,
                    "source_label": label,
                    "size_bytes": info.file_size,
                }
            )

    valid_entries.sort(
        key=lambda item: (
            item["participant_code"],
            item["view_angle"],
            not item["source_label"],
            item["archive_path"],
        )
    )

    result["files"] = valid_entries
    result["file_count"] = len(valid_entries)

    participants = {item["participant_code"] for item in valid_entries}

    result["participant_count"] = len(participants)

    for item in valid_entries:
        result["by_angle"][item["view_angle"]] += 1

        label_key = "good" if item["source_label"] else "bad"
        result["by_label"][label_key] += 1

    if not valid_entries:
        result["errors"].append("No supported video files were found in the archive.")

    observed = {
        (
            item["participant_code"],
            item["view_angle"],
            item["source_label"],
        )
        for item in valid_entries
    }

    missing = sum(
        1
        for participant in participants
        for angle in ANGLE_NAMES
        for label in (True, False)
        if (participant, angle, label) not in observed
    )

    if missing:
        result["warnings"].append(
            f"{missing} expected participant/view/label "
            "combinations have no matching video. Check this against "
            "your actual collection before importing."
        )

    if result["ignored_file_count"]:
        result["warnings"].append(
            f"{result['ignored_file_count']} non-video file(s) will be ignored."
        )

    if not any(result["by_label"].values()):
        result["errors"].append("No labelled video files could be identified.")

    return result


def staging_directory():
    directory = Path(settings.MEDIA_ROOT) / "dataset_import_staging"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def staged_archive_path(token):
    from uuid import UUID

    safe_token = UUID(str(token)).hex
    return staging_directory() / f"{safe_token}.zip"


def create_archive_preview(*, uploaded_file, user):
    if uploaded_file.size > MAX_ARCHIVE_BYTES:
        raise ValidationError({"zip_file": "The ZIP archive exceeds the size limit."})

    directory = staging_directory()
    token = uuid.uuid4()

    archive_path = staged_archive_path(token)
    temporary_path = directory / f"{token.hex}.tmp"
    metadata_path = directory / f"{token.hex}.json"
    metadata_temp = directory / f"{token.hex}.json.tmp"

    try:
        total_size = 0

        with temporary_path.open("wb") as destination:
            for chunk in uploaded_file.chunks(chunk_size=UPLOAD_CHUNK_SIZE):
                total_size += len(chunk)

                if total_size > MAX_ARCHIVE_BYTES:
                    raise ValidationError(
                        {"zip_file": "The ZIP archive exceeds the size limit."}
                    )

                destination.write(chunk)

        if not zipfile.is_zipfile(temporary_path):
            raise ValidationError(
                {"zip_file": "The uploaded file is not a valid ZIP archive."}
            )

        manifest = inspect_archive(temporary_path)

        videos = [
            {
                "archive_path": item["archive_path"],
                "participant_code": item["participant_code"],
                "angle_variant": item["view_angle"],
                "source_label": item["source_label"],
            }
            for item in manifest["files"]
        ]

        expires_at = timezone.now() + PREVIEW_TTL

        with metadata_temp.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "user_id": user.pk,
                    "expires_at": expires_at.timestamp(),
                    "manifest": manifest,
                    "videos": videos,
                },
                file,
            )

        temporary_path.replace(archive_path)
        metadata_temp.replace(metadata_path)

        return {
            "upload_token": str(token),
            "expires_at": expires_at.timestamp(),
            "manifest": manifest,
        }

    except Exception:
        temporary_path.unlink(missing_ok=True)
        metadata_temp.unlink(missing_ok=True)

        if not metadata_path.exists():
            archive_path.unlink(missing_ok=True)

        raise
