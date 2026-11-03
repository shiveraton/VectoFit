from django.core.management.base import BaseCommand, CommandError

from apps.training.services.experiment_runner import run_demo, run_experiment


class Command(BaseCommand):
    help = "Run the frozen M0/M1 LOPO experiment, or write a synthetic demo bundle."

    def add_arguments(self, parser):
        parser.add_argument("--config")
        parser.add_argument("--out", required=True)
        parser.add_argument("--demo", action="store_true")

    def handle(self, *args, **opts):
        if opts["demo"]:
            run_demo(opts["out"])
        elif opts["config"]:
            run_experiment(opts["config"], opts["out"])
        else:
            raise CommandError("Pass --config, or --demo for a synthetic bundle.")
        self.stdout.write(self.style.SUCCESS(f"Bundle written to {opts['out']}"))