from django.core.management.base import BaseCommand, CommandError

from apps.datasets.models import Dataset
from apps.datasets.services.consensus import apply_consensus, evaluate_sample


class Command(BaseCommand):
    help = "Resolve per-annotator knee annotations by consensus."

    def add_arguments(self, parser):
        parser.add_argument("--dataset", required=True, type=int)
        parser.add_argument("--min-annotators", type=int)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        dataset = Dataset.objects.filter(pk=options["dataset"]).first()
        if not dataset:
            raise CommandError("Dataset not found.")
        counts = {
            key: 0
            for key in ("resolved", "insufficient", "disagreement", "not_trainable")
        }
        needs = []
        for sample in dataset.samples.all():
            result = evaluate_sample(sample, options["min_annotators"])
            counts[result["status"]] += 1
            if result["status"] in {"disagreement", "not_trainable"}:
                needs.append(sample.pk)
            if not options["dry_run"]:
                apply_consensus(sample, result, force=options["force"])
        self.stdout.write(f"Counts: {counts}; samples needing adjudication: {needs}")
