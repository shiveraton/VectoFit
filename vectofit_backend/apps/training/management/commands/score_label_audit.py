import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.training.services.label_audit import score_label_audit


class Command(BaseCommand):
    help = "Score two independent rubric reviews against frozen labels and against each other."

    def add_arguments(self, parser):
        parser.add_argument("--manifest", required=True)
        parser.add_argument("--review-a", required=True)
        parser.add_argument("--review-b", required=True)
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        def read(name):
            return json.loads(Path(options[name]).read_text(encoding="utf-8"))
        report = score_label_audit(read("manifest"), {"A": read("review_a"), "B": read("review_b")})
        rendered = json.dumps(report, indent=2) + "\n"
        Path(options["output"]).write_text(rendered, encoding="utf-8")
        self.stdout.write(rendered)
