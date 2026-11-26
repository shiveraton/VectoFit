from pathlib import Path

import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut
from xgboost import XGBClassifier

from apps.analytics.services.feature_schemas import schema_for_target
from apps.training.services.trainer import train_and_evaluate

from ..config import default_hyperparameters, locked_hyperparameters
from ..services.data_loader import build_samples, resolve_datasets
from ..models import TrainingJob

TARGET = "knee_alignment"


def _first_attr(obj, names):
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    available = [a for a in dir(obj) if not a.startswith("_")]
    raise AttributeError(f"sample_set has none of {names}. Available: {available}")


def load_training_frame(dataset_id, features=None):
    datasets = resolve_datasets([dataset_id])
    schema = schema_for_target(TARGET)
    selected = [f for f in schema.feature_order if not features or f in features]
    sample_set = build_samples(
        datasets=datasets,
        selected_features=selected,
        view_angle="frontal",
        prediction_target=TARGET,
    )

    X = np.asarray(sample_set.rows, dtype=float)
    y = np.asarray(
        _first_attr(sample_set, ("labels", "y", "targets", "target"))
    ).astype(int)

    meta = pd.DataFrame(sample_set.sample_metadata)
    meta.insert(0, "sample_id", list(sample_set.sample_ids))

    for name in ("groups", "participants", "participant_ids"):
        if hasattr(sample_set, name):
            groups = np.asarray(getattr(sample_set, name))
            break
    else:
        col = next(
            (
                c
                for c in ("participant", "participant_id", "participant_name")
                if c in meta.columns
            ),
            None,
        )
        if col is None:
            raise KeyError(
                f"No participant field. sample_metadata keys: {list(meta.columns)}"
            )
        groups = meta[col].to_numpy()
    meta["participant"] = groups
    return X, y, groups, meta


def model_params():
    params = {**default_hyperparameters(), **locked_hyperparameters(TARGET, 2)}
    params.pop("scale_pos_weight", None)  # recomputed per fold below
    params.setdefault("random_state", 42)
    return params


def run_training_job(job):
    job.status = TrainingJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    dataset_ids = job.datasets.values_list("pk", flat=True)
    datasets = resolve_datasets(dataset_ids)

    sample_set = build_samples(
        datasets=datasets,
        selected_features=job.feature_selection,
        view_angle=job.view_angle or None,
        prediction_target=job.prediction_target,
    )

    result = train_and_evaluate(
        sample_set,
        hyperparameters=job.hyperparameters,
        split_strategy=job.split_strategy,
        test_size=job.test_size,
    )
    job.status = TrainingJob.Status.COMPLETED
    job.completed_at = timezone.now()

    job.metrics = result["metrics"]
    job.hyperparameters = result["hyperparameters"]
    job.feature_selection = result["feature_names"]
    job.train_count = len(result["train_idx"])
    job.test_count = len(result["test_idx"])
    job.sample_count = len(sample_set.rows)
    job.save(
        update_fields=[
            "status",
            "completed_at",
            "metrics",
            "hyperparameters",
            "feature_selection",
            "train_count",
            "test_count",
            "sample_count",
        ]
    )


class Command(BaseCommand):
    help = "Out-of-fold predictions and confident-error list (participant-grouped)."

    def add_arguments(self, parser):
        parser.add_argument("--dataset", type=int, required=True)
        parser.add_argument("--split", choices=["gkf5", "lopo"], default="gkf5")
        parser.add_argument("--features", nargs="*")
        parser.add_argument("--out", default="outputs/audit")
        parser.add_argument("--top", type=int, default=20)

    def handle(self, *args, **opts):
        X, y, groups, meta = load_training_frame(opts["dataset"], opts["features"])
        splitter = (
            LeaveOneGroupOut() if opts["split"] == "lopo" else GroupKFold(n_splits=5)
        )
        params = model_params()

        proba = np.zeros(len(y))
        for tr, te in splitter.split(X, y, groups):
            spw = (y[tr] == 0).sum() / max((y[tr] == 1).sum(), 1)
            model = XGBClassifier(scale_pos_weight=spw, **params)
            model.fit(X[tr], y[tr])
            proba[te] = model.predict_proba(X[te])[:, 1]

        pred = (proba >= 0.5).astype(int)
        df = meta.reset_index(drop=True).assign(
            y=y,
            p_bad=proba,
            pred=pred,
            conf=np.where(pred == 1, proba, 1 - proba),
            wrong=pred != y,
        )

        out = Path(opts["out"])
        out.mkdir(parents=True, exist_ok=True)
        tag = opts["split"]
        df.to_csv(out / f"oof_predictions_{tag}.csv", index=False)
        df[df.wrong].sort_values("conf", ascending=False).head(opts["top"]).to_csv(
            out / f"top_confident_errors_{tag}.csv", index=False
        )
        (
            df.groupby("participant")
            .agg(n=("y", "size"), error_rate=("wrong", "mean"))
            .sort_values("error_rate", ascending=False)
            .to_csv(out / f"error_by_participant_{tag}.csv")
        )

        baseline = max(y.mean(), 1 - y.mean())
        self.stdout.write(
            f"{tag}: acc={accuracy_score(y, pred):.3f} "
            f"macroF1={f1_score(y, pred, average='macro'):.3f} "
            f"majority_baseline={baseline:.3f} n={len(y)}"
        )
        self.stdout.write(f"Wrote 3 CSVs to {out.resolve()}")
