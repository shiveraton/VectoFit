import argparse
import os

import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)
django.setup()

from apps.training.services.data_loader import resolve_datasets
from apps.training.services.evaluation import (
    format_readiness_report,
    readiness_report,
)

parser = argparse.ArgumentParser(
    description=(
        "Frontal dataset audit: label/provenance audit, then a dry run of the "
        "fppa_v2 feature pipeline (no model is trained, nothing is written)."
    )
)
parser.add_argument("--view-angle", default="frontal")
parser.add_argument(
    "--prediction-target", choices=["binary_form", "error_type"], default="binary_form"
)
parser.add_argument(
    "--skip-label-audit",
    action="store_true",
    help="Only run the feature-pipeline readiness check.",
)
args = parser.parse_args()

audit_globals = {}
if not args.skip_label_audit:
    script_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "audit_frontal_fppa.py",
    )
    with open(script_path, encoding="utf-8") as f:
        code = compile(f.read(), script_path, "exec")
    audit_globals = {"__name__": "__main__", "__file__": script_path}
    exec(code, audit_globals)

dataset_id = audit_globals.get("DATASET_ID", 17)
datasets = resolve_datasets([dataset_id])

print("\n5. FEATURE PIPELINE READINESS (fppa_v2, dry run)")
for model_version in ("M0", "M1"):
    report = readiness_report(
        datasets,
        view_angle=args.view_angle,
        prediction_target=args.prediction_target,
        model_version=model_version,
    )
    print(format_readiness_report(report))
