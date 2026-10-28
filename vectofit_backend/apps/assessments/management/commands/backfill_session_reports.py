import logging

from django.core.management.base import BaseCommand, CommandError

from apps.analytics.services.session_report import build_session_report
from apps.assessments.models import AssessmentSession

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Rebuild session reports for completed assessments "
        "from their saved per-rep analysis results."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Build reports without writing them to the database.",
        )
        parser.add_argument(
            "--session-id",
            type=int,
            default=None,
            help="Restrict the backfill to one session ID.",
        )

    def handle(self, *args, **options):
        queryset = (
            AssessmentSession.objects.filter(status=AssessmentSession.Status.COMPLETED)
            .select_related("exercise_variant")
            .prefetch_related("reps")
            .order_by("pk")
        )

        if options["session_id"] is not None:
            queryset = queryset.filter(pk=options["session_id"])

        dry_run = options["dry_run"]
        updated = 0
        unchanged = 0
        failed = 0

        for session in queryset:
            try:
                report = build_session_report(
                    session.reps.all(),
                    session.exercise_variant.get_thresholds(),
                )

                if report == session.report:
                    unchanged += 1
                    continue

                if not dry_run:
                    session.report = report
                    session.save(update_fields=["report"])

                updated += 1

                action = "Would update" if dry_run else "Updated"
                self.stdout.write(f"{action} session #{session.pk}")

            except Exception as exc:
                failed += 1
                logger.exception(
                    "Backfill failed for session=%s",
                    session.pk,
                )
                self.stderr.write(self.style.ERROR(f"Session #{session.pk}: {exc}"))

        prefix = "Dry run complete" if dry_run else "Backfill complete"

        self.stdout.write(
            f"{prefix}. Changed: {updated}; unchanged: {unchanged}; failed: {failed}."
        )

        if failed:
            raise CommandError(f"{failed} session report(s) could not be rebuilt.")
