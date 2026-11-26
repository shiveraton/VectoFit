import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.datasets.models import DatasetAnnotatorAssignment, DatasetSample
from apps.datasets.services.knee_label import knee_label_evidence
from apps.training.services.label_audit import select_audit_samples


class Command(BaseCommand):
    help = "Freeze label provenance and prepare two blinded source-stratified rubric review files."

    def add_arguments(self, parser):
        parser.add_argument("--dataset-id", type=int, required=True)
        parser.add_argument("--eligibility-report", required=True)
        parser.add_argument("--output-dir", required=True)
        parser.add_argument("--per-source", type=int, default=20)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        output = Path(options["output_dir"])
        if output.exists():
            raise CommandError("Output directory already exists; preserve the frozen audit or choose a new directory.")
        eligible = set(json.loads(Path(options["eligibility_report"]).read_text())["eligible_sample_ids"])
        rows = []
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            samples = DatasetSample.objects.filter(dataset_id=options["dataset_id"]).select_related(
                "dataset_video", "rep_assessment"
            ).prefetch_related("knee_annotation_records").order_by("pk")
            for sample in samples:
                video = sample.dataset_video
                path = video.source_path if video else ""
                source = Path(path).name.split("_")[0].lower() or "unknown"
                evidence = knee_label_evidence(sample)
                rows.append({
                    "sample_id": sample.pk, "source": source,
                    "source_path": path, "source_label": video.source_label if video else None,
                    "is_correct": sample.is_correct,
                    "participant_id": video.participant_id if video else None,
                    "dataset_video_id": sample.dataset_video_id,
                    "rep_number": sample.rep_assessment.rep_number,
                    "start_frame": sample.rep_assessment.start_frame,
                    "end_frame": sample.rep_assessment.end_frame,
                    "target": evidence["target"], "annotations": evidence["annotations"],
                    "eligible": sample.pk in eligible,
                })
            assignments = list(DatasetAnnotatorAssignment.objects.filter(
                dataset_id=options["dataset_id"], is_active=True
            ).values("annotator_id"))
        candidates = [r for r in rows if r["eligible"] and r["target"] in {"good", "bad"}]
        selected = select_audit_samples(candidates, options["per_source"], options["seed"])
        for index, row in enumerate(selected, 1):
            row["audit_id"] = f"R{index:03d}"
        summary = {}
        for source in sorted({r["source"] for r in rows}):
            source_rows = [r for r in rows if r["source"] == source]
            summary[source] = {
                "samples": len(source_rows),
                "targets": dict(Counter(r["target"] for r in source_rows)),
                "source_labels": dict(Counter(str(r["source_label"]) for r in source_rows)),
                "rubric_versions": dict(Counter(a["rubric_version"] for r in source_rows for a in r["annotations"])),
                "annotator_ids": sorted({a["annotator_id"] for r in source_rows for a in r["annotations"] if a["annotator_id"] is not None}),
            }
        manifest = {
            "dataset_id": options["dataset_id"], "frozen_at": datetime.now(timezone.utc).isoformat(),
            "seed": options["seed"], "selection": "Equal source quotas, randomized participant round-robin, training-eligible binary targets only",
            "active_assignments": assignments, "provenance_summary": summary,
            "samples": selected,
        }
        output.mkdir(parents=True)
        def write(name, value):
            (output / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        write("private_manifest.json", manifest)
        write("private_provenance.json", rows)
        for annotator in ("A", "B"):
            write(f"review_{annotator}.json", {
                "annotator": annotator,
                "instructions": "Independently rate both knees using the current knee rubric. Do not consult previous labels, folder versions, the other reviewer, or model output. Return this file; do not overwrite production annotations.",
                "samples": [{
                    "audit_id": r["audit_id"], "sample_id": r["sample_id"],
                    "rep_number": r["rep_number"],
                    "annotation": {"notes": "", **{side: {"grade": None, "direction": None} for side in ("left", "right")}},
                } for r in selected],
            })
        self.stdout.write(json.dumps({"sources": summary, "selected": dict(Counter(r["source"] for r in selected)), "active_assignments": assignments}, indent=2))
        self.stdout.write(f"Prepared audit in {output}; no production records changed.")
