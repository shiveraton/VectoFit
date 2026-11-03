import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.assessments.models import AssessmentSession
from apps.datasets.models import DatasetSample


def _event_row(event):
    return {
        "id": event.pk,
        "annotator_id": event.annotator_id,
        "entered_by_id": event.entered_by_id,
        "action": event.action,
        "target_label": event.target_label,
        "payload": event.payload,
        "rubric_version": event.rubric_version,
        "created_at": event.created_at.isoformat(),
    }


def _sample_row(sample):
    video = sample.dataset_video
    return {
        "sample_id": sample.pk,
        "video_id": sample.dataset_video_id,
        "participant": video.participant.participant_code if video else None,
        "source_label": video.source_label if video else None,
        "is_correct": sample.is_correct,
        "label_source": sample.label_source,
        "error_label": sample.error_label,
        "annotator_id": sample.annotator_id,
        "annotated_at": sample.annotated_at.isoformat()
        if sample.annotated_at
        else None,
        "knee_annotations": [
            {
                "id": row.pk,
                "annotator_id": row.annotator_id,
                "annotation": row.annotation,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            }
            for row in sample.knee_annotations.all().order_by("id")
        ],
        "events": [
            _event_row(row) for row in sample.annotation_events.all().order_by("id")
        ],
    }


def _timestamp_by_frame(rep):
    landmark_data = rep.landmark_data
    if not isinstance(landmark_data, dict):
        return {}
    return {
        frame["frame_index"]: frame["timestamp_ms"]
        for frame in landmark_data.get("frames", [])
    }


class Command(BaseCommand):
    help = "Export dataset 17 session, rep, label, landmark and annotation fixtures to JSON."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="dataset_17_pilot_fixtures.json")

    def handle(self, *args, **options):
        output = Path(options["output"]).expanduser().resolve()
        sessions = (
            AssessmentSession.objects.filter(dataset_id=17)
            .select_related("dataset", "user", "exercise_variant")
            .prefetch_related("reps")
        )
        all_samples = list(
            DatasetSample.objects.filter(dataset_id=17)
            .select_related("dataset_video__participant")
            .prefetch_related("knee_annotations", "annotation_events")
            .order_by("id")
        )
        samples_by_id = {sample.pk: sample for sample in all_samples}
        result = {"dataset_id": 17, "sessions": [], "samples": []}
        for session in sessions.order_by("id"):
            reps = []
            for rep in session.reps.all().order_by("rep_number"):
                samples = [
                    samples_by_id[sample_id]
                    for sample_id in rep.dataset_sample.values_list("id", flat=True)
                    if sample_id in samples_by_id
                ]
                timestamps = _timestamp_by_frame(rep)
                reps.append(
                    {
                        "rep_id": rep.pk,
                        "rep_number": rep.rep_number,
                        "video_id": samples[0].dataset_video_id if samples else None,
                        "participant": samples[
                            0
                        ].dataset_video.participant.participant_code
                        if samples and samples[0].dataset_video
                        else None,
                        "labels": [_sample_row(sample) for sample in samples],
                        "start_frame": rep.start_frame,
                        "end_frame": rep.end_frame,
                        "start_timestamp_ms": timestamps.get(rep.start_frame),
                        "end_timestamp_ms": timestamps.get(rep.end_frame),
                        "key_frame_index": rep.key_frame_index,
                        "landmark_series": rep.landmark_series,
                        "landmark_data": rep.landmark_data,
                        "landmark_schema_version": rep.landmark_schema_version,
                        "pipeline_config_hash": rep.pipeline_config_hash,
                    }
                )
            result["sessions"].append(
                {
                    "session_id": session.pk,
                    "video": session.video_file.name,
                    "participant": reps[0]["participant"] if reps else None,
                    "processed_frame_width": session.processed_frame_width,
                    "processed_frame_height": session.processed_frame_height,
                    "pipeline_config_hash": session.pipeline_config_hash,
                    "reps": reps,
                }
            )
        result["samples"] = [_sample_row(sample) for sample in all_samples]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self.stdout.write(
            self.style.SUCCESS(f"Exported dataset 17 fixtures to {output}")
        )
