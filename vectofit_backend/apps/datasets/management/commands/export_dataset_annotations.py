import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.datasets.models import DatasetSample, DatasetVideo, KneeAnnotation
from apps.datasets.services.knee_label import knee_target

REP_FIELDS = [
    "video_id",
    "dataset_video_id",
    "participant_id",
    "source",
    "view",
    "filename",
    "sample_id",
    "rep_assessment_id",
    "rep_number",
    "start_frame",
    "end_frame",
]
RATING_FIELDS = REP_FIELDS + [
    "annotator",
    "record_id",
    "created_at",
    "rubric_version",
    "rating_status",
    "left_grade",
    "left_direction",
    "right_grade",
    "right_direction",
    "symmetry_observation",
    "notes",
    "target",
    "annotation_json",
]


def read_csv(path, required):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        duplicates = sorted(
            name for name, count in Counter(headers).items() if count > 1
        )
        if duplicates:
            raise CommandError(f"{path} has duplicate columns: {', '.join(duplicates)}")
        if not required.issubset(headers):
            raise CommandError(
                f"{path} requires columns: {', '.join(sorted(required))}"
            )
        rows = list(reader)
    if not rows:
        raise CommandError(f"{path} has no rows.")
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise CommandError(f"{path} contains malformed rows.")
    return rows


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rating_row(rep, pseudonym, record):
    annotation = record.annotation if record else None
    payload = annotation if isinstance(annotation, dict) else {}
    status = "missing"
    if record is not None:
        status = "cleared" if annotation is None else "rated"
    row = {
        **rep,
        "annotator": pseudonym,
        "record_id": record.pk if record else "",
        "created_at": record.created_at.isoformat() if record else "",
        "rubric_version": record.rubric_version if record else "",
        "rating_status": status,
        "symmetry_observation": payload.get("symmetry_observation", ""),
        "notes": payload.get("notes", ""),
        "target": knee_target(annotation) if annotation is not None else "",
        "annotation_json": json.dumps(annotation, ensure_ascii=False, sort_keys=True)
        if record
        else "",
    }
    for side in ("left", "right"):
        knee = payload.get(side)
        knee = knee if isinstance(knee, dict) else {}
        for field in ("grade", "direction"):
            row[f"{side}_{field}"] = knee.get(field, "")
    return row


class Command(BaseCommand):
    help = (
        "Export manifest-linked repetitions and current per-annotator rating snapshots."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dataset-id", required=True, type=int)
        parser.add_argument("--manifest", required=True, type=Path)
        parser.add_argument("--output", required=True, type=Path)
        parser.add_argument(
            "--annotator", required=True, action="append", help="USER_ID=annotator_01"
        )
        parser.add_argument(
            "--video-map", type=Path, help="Optional CSV: video_id,dataset_video_id"
        )
        parser.add_argument("--history", action="store_true")

    def handle(self, *args, **options):
        try:
            self.export(options)
        except (OSError, UnicodeError, csv.Error) as error:
            raise CommandError(str(error)) from error

    def export(self, options):
        output = options["output"]
        if output.exists():
            raise CommandError(
                "Output already exists; choose a new snapshot directory."
            )
        manifest_path = options["manifest"]
        manifest_bytes = manifest_path.read_bytes()
        manifest = read_csv(
            manifest_path, {"video_id", "participant_id", "source", "view", "filename"}
        )
        for field in ("video_id", "filename"):
            values = [row[field] for row in manifest]
            if any(not value.strip() for value in values) or len(set(values)) != len(
                values
            ):
                raise CommandError(
                    f"Manifest {field} values must be nonempty and unique."
                )

        annotators = {}
        for value in options["annotator"]:
            match = re.fullmatch(r"([1-9][0-9]*)=(annotator_[0-9]{2,})", value)
            if not match:
                raise CommandError("Use --annotator USER_ID=annotator_01.")
            user_id, pseudonym = int(match[1]), match[2]
            if user_id in annotators or pseudonym in annotators.values():
                raise CommandError("Annotator IDs and pseudonyms must be unique.")
            annotators[user_id] = pseudonym
        if get_user_model().objects.filter(pk__in=annotators).count() != len(
            annotators
        ):
            raise CommandError("An annotator account does not exist.")

        overrides = {}
        if options["video_map"]:
            for row in read_csv(options["video_map"], {"video_id", "dataset_video_id"}):
                if row["video_id"] in overrides or not re.fullmatch(
                    r"[1-9][0-9]*", row["dataset_video_id"]
                ):
                    raise CommandError(
                        "Video mapping requires unique video IDs and integer database IDs."
                    )
                overrides[row["video_id"]] = int(row["dataset_video_id"])
            if set(overrides) - {row["video_id"] for row in manifest}:
                raise CommandError("Video mapping contains IDs outside the manifest.")

        videos = list(
            DatasetVideo.objects.filter(
                dataset_id=options["dataset_id"]
            ).select_related("participant", "view_angle")
        )
        mapped = {}
        used = set()
        for row in manifest:
            if row["video_id"] in overrides:
                candidates = [
                    video for video in videos if video.pk == overrides[row["video_id"]]
                ]
            else:
                candidates = [
                    video
                    for video in videos
                    if PurePosixPath(video.source_path.replace("\\", "/")).name
                    == PurePosixPath(row["filename"]).name
                ]
            if len(candidates) != 1:
                raise CommandError(
                    f"{row['video_id']}: expected one database video; use --video-map to resolve."
                )
            video = candidates[0]
            if video.pk in used:
                raise CommandError(
                    "Multiple manifest videos map to the same database video."
                )
            if (
                video.participant.participant_code.casefold()
                != row["participant_id"].casefold()
            ):
                raise CommandError(
                    f"{row['video_id']}: database participant does not match the manifest."
                )
            if video.view_angle.angle_variant != row["view"]:
                raise CommandError(
                    f"{row['video_id']}: database view does not match the manifest."
                )
            if video.status != DatasetVideo.Status.READY:
                raise CommandError(f"{row['video_id']}: database video is not READY.")
            used.add(video.pk)
            mapped[video.pk] = row

        samples = list(
            DatasetSample.objects.filter(
                dataset_id=options["dataset_id"], dataset_video_id__in=mapped
            )
            .select_related("rep_assessment")
            .order_by("dataset_video_id", "rep_assessment__rep_number", "pk")
        )
        repetitions = {}
        for sample in samples:
            rep = sample.rep_assessment
            if (
                rep.start_frame is None
                or rep.end_frame is None
                or rep.start_frame >= rep.end_frame
            ):
                raise CommandError(
                    f"Sample {sample.pk} requires valid repetition frame boundaries."
                )
            row = mapped[sample.dataset_video_id]
            repetitions[sample.pk] = {
                **{
                    field: row[field]
                    for field in (
                        "video_id",
                        "participant_id",
                        "source",
                        "view",
                        "filename",
                    )
                },
                "dataset_video_id": sample.dataset_video_id,
                "sample_id": sample.pk,
                "rep_assessment_id": rep.pk,
                "rep_number": rep.rep_number,
                "start_frame": rep.start_frame,
                "end_frame": rep.end_frame,
            }
        if {sample.dataset_video_id for sample in samples} != set(mapped):
            raise CommandError(
                "Every manifest video must have at least one segmented sample."
            )

        cutoff = timezone.now()
        records = list(
            KneeAnnotation.objects.filter(
                sample_id__in=repetitions,
                annotator_id__in=annotators,
                created_at__lte=cutoff,
            ).order_by("created_at", "id")
        )
        latest = {}
        for record in records:
            latest[record.sample_id, record.annotator_id] = record

        output.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(
            prefix=".annotation-export-", dir=output.parent
        ) as temporary:
            staging = Path(temporary) / "snapshot"
            staging.mkdir()
            write_csv(staging / "repetitions.csv", REP_FIELDS, repetitions.values())
            for user_id, pseudonym in sorted(annotators.items()):
                write_csv(
                    staging / f"{pseudonym}.csv",
                    RATING_FIELDS,
                    [
                        rating_row(rep, pseudonym, latest.get((sample_id, user_id)))
                        for sample_id, rep in repetitions.items()
                    ],
                )
            if options["history"]:
                write_csv(
                    staging / "history.csv",
                    RATING_FIELDS,
                    [
                        rating_row(
                            repetitions[record.sample_id],
                            annotators[record.annotator_id],
                            record,
                        )
                        for record in records
                    ],
                )
            metadata = {
                "schema_version": 1,
                "exported_at": cutoff.isoformat(),
                "dataset_id": options["dataset_id"],
                "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                "selection_policy": "Latest created_at then ID per sample/annotator at exported_at; cleared and missing ratings retained.",
                "annotators": sorted(annotators.values()),
                "video_count": len(mapped),
                "repetition_count": len(repetitions),
                "history_included": options["history"],
                "sha256": {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(staging.glob("*.csv"))
                },
            }
            (staging / "snapshot.json").write_text(
                json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
            )
            staging.rename(output)
        self.stdout.write(
            f"Saved {len(repetitions)} repetitions and {len(annotators)} annotator snapshots to {output}"
        )
