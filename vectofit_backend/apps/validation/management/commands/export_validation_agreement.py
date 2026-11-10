import csv
from collections import Counter
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.validation.agreement import agreement_metrics, consensus_labels
from apps.validation.models import ValidationAnnotation, ValidationSample


class Command(BaseCommand):
    help = "Export expert versus current human consensus agreement, with excluded pairs reported."

    def add_arguments(self, parser):
        parser.add_argument("--validator", required=True, help="Validator username")
        parser.add_argument("--output", required=True, type=Path)

    @transaction.atomic
    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["validator"]).first()
        if user is None:
            raise CommandError("Validator account not found.")
        selections = list(ValidationSample.objects.select_related("repetition").prefetch_related(
            "repetition__knee_annotation_records"))
        if not selections:
            raise CommandError("No frozen validation sample exists.")
        ratings = {row.repetition_id: row for row in ValidationAnnotation.objects.filter(validator=user)}
        scopes = {
            "left_knee": ValidationAnnotation.Knee.values,
            "right_knee": ValidationAnnotation.Knee.values,
            "overall": {"good", "bad", "borderline", "unassessable"},
            "overall_good_bad": {"good", "bad"},
        }
        details = []
        for selection in selections:
            rating = ratings.get(selection.repetition_id)
            reference = consensus_labels(selection.repetition)
            for scope, valid_labels in scopes.items():
                field = "overall" if scope == "overall_good_bad" else scope
                expert = getattr(rating, field) if rating else "missing_validation"
                consensus = reference[field]
                reason = ""
                if rating is None:
                    reason = "missing_validation"
                elif rating.protocol_version != selection.protocol_version:
                    reason = "protocol_mismatch"
                elif consensus not in valid_labels:
                    reason = f"consensus_{consensus}"
                elif expert not in valid_labels:
                    reason = f"validation_{expert}"
                details.append({"repetition_id": selection.repetition_id,
                                "assessment_rep_id": selection.repetition.rep_assessment_id,
                                "validator_id": user.pk, "protocol_version": selection.protocol_version,
                                "scope": scope, "validation_label": expert, "consensus_label": consensus,
                                "included": not reason, "exclusion_reason": reason,
                                "agreement": expert == consensus if not reason else ""})
        summary = []
        for scope in scopes:
            rows = [row for row in details if row["scope"] == scope]
            pairs = [(row["validation_label"], row["consensus_label"]) for row in rows if row["included"]]
            excluded = Counter(row["exclusion_reason"] for row in rows if not row["included"])
            summary.append({"validator_id": user.pk, "scope": scope, "sample_count": len(selections),
                            **agreement_metrics(pairs), "excluded_count": sum(excluded.values()),
                            "exclusions": "; ".join(f"{key}={value}" for key, value in sorted(excluded.items()))})
        output = options["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        details_path = output.with_name(output.stem + "_pairs.csv")
        for path, rows in ((output, summary), (details_path, details)):
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        self.stdout.write(f"Saved {output} and {details_path}")
