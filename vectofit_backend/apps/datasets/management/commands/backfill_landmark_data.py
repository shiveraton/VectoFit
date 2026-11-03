import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.datasets.models import Dataset
from apps.datasets.services.video_processing import backfill_rep_landmark_data

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Backfill landmark_data for labelled repetitions that were created before "
        "the pipeline stored landmarks. Updates existing rows in place; never "
        "creates or deletes DatasetSample / RepAssessment / AssessmentSession rows "
        "and never touches is_correct / error_label / annotator / label_source."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset-id",
            required=True,
            type=int,
            help="Dataset ID to backfill.",
        )
        parser.add_argument(
            "--angle-variant",
            type=str,
            default="frontal",
            help="View angle variant to backfill (default: frontal).",
        )
        parser.add_argument(
            "--user-id",
            required=True,
            type=int,
            help="User ID performing the backfill (audit trail only).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be updated without writing to the database.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required safety flag to actually perform the backfill (non-dry-run).",
        )

    def handle(self, *args, **options):
        dataset_id = options["dataset_id"]
        angle_variant = options["angle_variant"]
        user_id = options["user_id"]
        dry_run = options["dry_run"]
        confirm = options["confirm"]

        if not dry_run and not confirm:
            raise CommandError(
                "Refusing to run without --confirm. "
                "Run with --dry-run to preview, or add --confirm to execute."
            )

        dataset = Dataset.objects.filter(pk=dataset_id).first()
        if not dataset:
            raise CommandError(f"Dataset {dataset_id} not found.")

        user = get_user_model().objects.filter(pk=user_id).first()
        if not user:
            raise CommandError(f"User {user_id} not found.")

        result = backfill_rep_landmark_data(
            dataset=dataset,
            user=user,
            angle_variant=angle_variant,
            dry_run=dry_run,
        )

        self.stdout.write(
            f"Dataset {result['dataset_id']} | angle={result['angle_variant']} | "
            f"dry_run={result['dry_run']}"
        )
        self.stdout.write(
            f"  total_samples:     {result['total_samples']}"
        )
        self.stdout.write(
            f"  updated_reps:      {result['updated_reps']}"
        )
        self.stdout.write(
            f"  skipped_mismatch:  {result['skipped_mismatch']}"
        )
        self.stdout.write(
            f"  skipped_no_video:  {result['skipped_no_video']}"
        )
        self.stdout.write(
            f"  skipped_no_session: {result['skipped_no_session']}"
        )

        for video in result["videos"]:
            status = "OK" if video["error"] is None else f"ERROR: {video['error']}"
            self.stdout.write(
                f"  video {video['video_id']} ({video['view_angle']}): "
                f"{video['samples']} samples, "
                f"{video['updated']} updated, "
                f"{video['skipped_mismatch']} mismatch, "
                f"{video['skipped_no_session']} no_session — {status}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete — no changes written."))
        elif result["updated_reps"] > 0:
            self.stdout.write(self.style.SUCCESS("Backfill complete."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Backfill complete — no reps were updated (check for mismatches)."
                )
            )