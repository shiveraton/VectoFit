import json

from django.core.management.base import BaseCommand, CommandError

from apps.datasets.models import Dataset
from apps.datasets.services.agreement import agreement_for_dataset


class Command(BaseCommand):
    help = "Report inter-annotator agreement for a dataset."

    def add_arguments(self, parser):
        parser.add_argument("--dataset", required=True, type=int)
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        dataset = Dataset.objects.filter(pk=options["dataset"]).first()
        if not dataset:
            raise CommandError("Dataset not found.")
        result = agreement_for_dataset(dataset)
        self.stdout.write(
            json.dumps(result, indent=2 if options["json"] else None, sort_keys=True)
        )
