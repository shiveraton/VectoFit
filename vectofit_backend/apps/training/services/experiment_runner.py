from __future__ import annotations

import csv
import hashlib
import io
import json
import platform
import subprocess
from datetime import UTC, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import lopo_evaluator as ev
from apps.training.services.data_loader import resolve_datasets
from apps.training.services.evaluation import build_paired_sample_sets
from apps.training.services.trainer import train_and_evaluate


def load_rep_table(cfg):
    d = cfg["data"]
    if d["source"] == "csv":
        return pd.read_csv(d["csv_path"])
    from apps.training.services import (
        data_loader,
    )

    return data_loader.load_rep_feature_table(
        feature_schema_version=d["feature_schema_version"], view_angle=d["view_angle"]
    )


def _prepare(cfg):
    df = load_rep_table(cfg)
    df = df.rename(columns={v: k for k, v in cfg["data"]["columns"].items()})
    m0, m1 = cfg["models"]["M0"]["features"], cfg["models"]["M1"]["features"]
    rule = cfg["rule_baseline"]["columns"]
    allcols = set(m0) | set(m1) | set(rule)
    if any("<" in c for c in allcols) or "<" in cfg.get("decision_rule", ""):
        raise ValueError("Config still contains <placeholders>.")
    if m1[: len(m0)] != m0 or len(m1) <= len(m0):
        raise ValueError("M1 must be M0 features plus extra asymmetry features.")
    missing = (allcols | {"rep_id", "participant_id", "label"}) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if df["rep_id"].duplicated().any():
        raise ValueError("Duplicate rep_id.")
    if not set(df["label"].unique()) <= {0, 1}:
        raise ValueError("label must be 0 (Good) / 1 (Bad).")
    if df[sorted(allcols)].isna().any().any():
        raise ValueError(
            "NaN in features; M0, M1 and the rule must see identical complete data."
        )
    df = df.sort_values("rep_id").reset_index(
        drop=True
    )  # canonical order -> deterministic folds
    return df


def _compare(df, cfg):
    x, u = cfg["xgb"], cfg["uncertainty"]
    o0 = ev.run_lopo_xgb(
        df,
        cfg["models"]["M0"]["features"],
        x["params"],
        cfg["seed"],
        x["decision_threshold"],
    )
    o1 = ev.run_lopo_xgb(
        df,
        cfg["models"]["M1"]["features"],
        x["params"],
        cfg["seed"],
        x["decision_threshold"],
    )
    assert (o0["rep_id"].to_numpy() == o1["rep_id"].to_numpy()).all(), (
        "M0/M1 folds diverged"
    )
    res = {
        "models": {"M0": ev.compute_metrics(o0), "M1": ev.compute_metrics(o1)},
        "delta_macro_f1_M1_minus_M0": {
            "bootstrap": ev.paired_bootstrap_delta(
                o0, o1, u["n_boot"], u["seed"], u["ci"]
            ),
            "jackknife": ev.jackknife_delta(o0, o1),
        },
    }
    return res, o0, o1


def _round(o):
    if isinstance(o, float):
        return round(o, 6)
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_round(v) for v in o]
    return o


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def run_from_sample_sets(m0, m1, cfg):
    seed = int(cfg.get("seed", 42))
    hyperparameters = cfg.get("hyperparameters")

    # Validate exclusion groups against the actual sample groups.
    exclude_groups = (cfg.get("sensitivity") or {}).get("exclude_groups", [])
    known_groups = set(m0.groups)
    for group in exclude_groups:
        if group not in known_groups:
            raise ValueError(f"Unknown exclusion group: {group}")

    r0 = train_and_evaluate(m0, hyperparameters, seed=seed, evaluation="lopo")
    r1 = train_and_evaluate(m1, hyperparameters, seed=seed, evaluation="lopo")

    if r0["oof"]["index"] != r1["oof"]["index"]:
        raise ValueError("M0 and M1 were evaluated on different samples.")

    index = list(r0["oof"]["index"])

    oof = {
        "sample_id": [m0.sample_ids[i] for i in index],
        "group": [str(m0.groups[i]) for i in index],
        "M0_pred": list(r0["oof"]["predicted"]),
        "M1_pred": list(r1["oof"]["predicted"]),
    }

    results = {
        "experiment_id": cfg.get("experiment_id", "experiment"),
        "hyperparameters_shared": r0["hyperparameters"],
        "main": {"lopo": dict(r0["evaluation"])},
        "demo": bool(cfg.get("demo", False)),
    }
    return results, oof


def write_bundle(out_dir, cfg_bytes, cfg, m0, m1, results, oof):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results_b = json.dumps(results, sort_keys=True, indent=2).encode()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(oof.keys())
    w.writerows(zip(*oof.values()))
    oof_b = buf.getvalue().encode()
    snapshot = sorted(
        [mt["sample_id"], int(bool(mt["is_correct"])), mt.get("label_source", "")]
        for mt in m0.sample_metadata
    )
    feat_b = json.dumps([m0.sample_ids, m1.rows, m1.groups, list(m1.labels)], separators=(",", ":")).encode()
    (out / "experiment_results.json").write_bytes(results_b)
    (out / "oof_predictions.csv").write_bytes(oof_b)
    (out / "experiment_report.md").write_text(render_report(results), encoding="utf-8")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = None
    import sklearn
    import xgboost
    (out / "provenance.json").write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(), "git_commit": commit,
        "demo": bool(cfg.get("demo", False)), "dataset_ids": cfg["dataset_ids"],
        "pipeline_config_hashes": dict(getattr(m0, "pipeline_config_hashes", None) or {}),
        "exclusion_counts": dict(getattr(m0, "exclusion_counts", None) or {}),
        "python": platform.python_version(), "numpy": np.__version__, "sklearn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "sha256": {"config": _sha(cfg_bytes), "feature_matrix": _sha(feat_b),
                   "label_snapshot": _sha(json.dumps(snapshot, separators=(",", ":")).encode()),
                   "oof_predictions": _sha(oof_b), "results": _sha(results_b)}}, indent=2), encoding="utf-8")


def run_experiment(config_path, out_dir):
    cfg_bytes = Path(config_path).read_bytes()
    cfg = json.loads(cfg_bytes)
    if "<" in json.dumps(cfg):
        raise ValueError("Config still contains <placeholders>.")
    if cfg["prediction_target"] != "binary_form":
        raise ValueError("Phase 3 comparison is binary_form only.")
    datasets = resolve_datasets(cfg["dataset_ids"])
    m0, m1 = build_paired_sample_sets(datasets, cfg["view_angle"], cfg["prediction_target"])
    results, oof = run_from_sample_sets(m0, m1, cfg)
    write_bundle(out_dir, cfg_bytes, cfg, m0, m1, results, oof)
    return results


def run_demo(out_dir):
    from .experiment_demo import synthetic_pair

    cfg = {
        "experiment_id": "demo_synthetic", "demo": True, "dataset_ids": [], "seed": 42, "n_jobs": 1,
        "label_semantics": "SYNTHETIC DEMO DATA. Not a result.", "decision_rule": "n/a (demo)",
        "uncertainty": {"n_boot": 10000, "seed": 1, "ci": 0.95},
        "rule_baseline": {"grid": {"start": 0.0, "stop": 20.0, "step": 0.5}},
        "sensitivity": {"exclude_groups": ["demo-4"]},
    }
    m0, m1 = synthetic_pair()
    results, oof = run_from_sample_sets(m0, m1, cfg)
    write_bundle(out_dir, json.dumps(cfg).encode(), cfg, m0, m1, results, oof)
    return results



def render_report(res):
    lines = []
    if res.get("demo"):
        lines.append("> SYNTHETIC DEMO DATA. These numbers are not results.")
        lines.append("")
    lines.append(f"# {res.get('experiment_id', 'experiment')} (exploratory pilot, LOPO)")
    lines.append("")
    main = res.get("main", {})
    lopo = main.get("lopo", {}) if isinstance(main, dict) else {}
    if isinstance(lopo, dict) and "n_folds" in lopo:
        lines.append(f"LOPO folds: {lopo['n_folds']}")
    lines.append("")
    return "\n".join(lines)
