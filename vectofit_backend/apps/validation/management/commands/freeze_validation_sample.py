from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.datasets.models import DatasetSample
from apps.datasets.services.assignments import review_samples
from apps.validation.models import ValidationSample


class Command(BaseCommand):
    help = "Freeze an explicit, ordered list of DatasetSample IDs for blinded validation."

    def add_arguments(self, parser):
        parser.add_argument("--repetition-ids", nargs="+", type=int, required=True)
        parser.add_argument("--protocol-version", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        ids = options["repetition_ids"]
        version = options["protocol_version"].strip()
        if not version or len(version) > 32 or len(ids) != len(set(ids)):
            raise CommandError("Supply a protocol version of 1-32 characters and unique repetition IDs.")
        existing = list(ValidationSample.objects.values_list("repetition_id", "protocol_version"))
        desired = [(pk, version) for pk in ids]
        if existing:
            if existing == desired:
                self.stdout.write("Validation sample already matches; no changes made.")
                return
            raise CommandError("The validation sample is already frozen; its membership cannot be replaced.")
        list(DatasetSample.objects.select_for_update().filter(pk__in=ids))
        eligible = set(review_samples().filter(pk__in=ids).values_list("pk", flat=True))
        missing = set(ids) - eligible
        if missing:
            raise CommandError(f"Unknown or ineligible frontal review repetitions: {sorted(missing)}")
        ValidationSample.objects.bulk_create([
            ValidationSample(repetition_id=pk, position=index, protocol_version=version)
            for index, pk in enumerate(ids)
        ])
        self.stdout.write(self.style.SUCCESS(f"Frozen {len(ids)} validation repetitions for {version}."))
