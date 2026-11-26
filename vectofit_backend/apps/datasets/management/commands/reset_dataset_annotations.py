import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from apps.datasets.models import Dataset, DatasetSample, KneeAnnotation


class Command(BaseCommand):
    help = "Back up and reset one annotator's ratings for one dataset; retain videos and repetitions."

    def add_arguments(self, parser):
        parser.add_argument("--dataset-id", type=int, required=True)
        parser.add_argument("--annotator-id", type=int, required=True)
        parser.add_argument("--backup", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        dataset = Dataset.objects.select_for_update().get(pk=options["dataset_id"])
        samples = DatasetSample.objects.filter(dataset=dataset)
        list(samples.select_for_update().values_list("pk", flat=True))
        records = KneeAnnotation.objects.filter(
            sample__dataset=dataset, annotator_id=options["annotator_id"]
        )
        ratings = list(records.select_for_update().values())
        if not ratings:
            raise CommandError("No matching ratings; nothing was changed.")
        backup = Path(options["backup"])
        backup.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dataset_id": dataset.pk, "dataset_name": dataset.name,
            "annotator_id": options["annotator_id"], "knee_annotations": ratings,
            "sample_labels": list(samples.filter(annotator_id=options["annotator_id"]).values(
                "id", "is_correct", "error_label", "annotator_id", "annotated_at"
            )),
        }
        with backup.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, cls=DjangoJSONEncoder, indent=2)
            handle.write("\n")
        records.delete()
        cleared = samples.filter(annotator_id=options["annotator_id"]).update(
            is_correct=None, error_label="", annotator=None, annotated_at=None
        )
        self.stdout.write(f"Reset {len(ratings)} knee ratings and {cleared} coarse labels for dataset {dataset.pk}. Backup: {backup}")
