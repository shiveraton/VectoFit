from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.datasets.models import AnnotationEvent, KneeAnnotation
from apps.datasets.services.annotation import derive_target_label


class Command(BaseCommand):
    help = "Reassign unowned knee annotations and record provenance events."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["username"]).first()
        if not user:
            raise CommandError("User not found.")
        rows = list(
            KneeAnnotation.objects.filter(annotator__isnull=True).select_related(
                "sample"
            )
        )
        assigned = skipped = 0
        for row in rows:
            if KneeAnnotation.objects.filter(
                sample=row.sample, annotator=user
            ).exists():
                skipped += 1
                continue
            if not options["dry_run"]:
                with transaction.atomic():
                    row.annotator = user
                    row.save(update_fields=["annotator"])
                    AnnotationEvent.objects.create(
                        sample=row.sample,
                        annotator=user,
                        entered_by=user,
                        action=AnnotationEvent.Action.REASSIGN,
                        target_label=derive_target_label(row.annotation) or "",
                        payload=row.annotation,
                        rubric_version=getattr(
                            settings, "ANNOTATION_RUBRIC_VERSION", "v1"
                        ),
                    )
            assigned += 1
        self.stdout.write(
            f"{'Would reassign' if options['dry_run'] else 'Reassigned'} {assigned}; skipped {skipped}."
        )
