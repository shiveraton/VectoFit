import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.training.services.data_loader import prepare_knee_samples, resolve_datasets


class Command(BaseCommand):
    help = "Audit frontal knee eligibility without changing annotations or running training."

    def add_arguments(self, parser):
        parser.add_argument("--dataset-ids", nargs="+", type=int, required=True)
        parser.add_argument("--output")

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SET TRANSACTION READ ONLY")
                datasets = resolve_datasets(options["dataset_ids"])
                report = prepare_knee_samples(datasets).readiness_report()
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        rendered = json.dumps(report, indent=2)
        if options["output"]:
            Path(options["output"]).write_text(rendered + "\n", encoding="utf-8")
            self.stdout.write(f"Wrote knee-readiness audit to {options['output']}")
        else:
            self.stdout.write(rendered)
