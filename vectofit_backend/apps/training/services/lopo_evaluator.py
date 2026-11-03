import itertools

import numpy as np

BAD, GOOD = 0, 1


def _f1(c):
    tp, fp, fn = c[..., 0], c[..., 1], c[..., 2]
    d = 2 * tp + fp + fn
    return np.divide(2 * tp, d, out=np.zeros_like(d, dtype=float), where=d > 0).mean(
        axis=-1
    )


def group_counts(y, pred, groups):
    ids = sorted(set(np.asarray(groups).tolist()))
    groups = np.asarray(groups)
    out = np.zeros((len(ids), 2, 3))
    for i, g in enumerate(ids):
        m = groups == g
        for c in (0, 1):
            out[i, c] = [
                np.sum(m & (y == c) & (pred == c)),
                np.sum(m & (y != c) & (pred == c)),
                np.sum(m & (y == c) & (pred != c)),
            ]
    return ids, out


def macro_f1(y, pred):
    _, c = group_counts(y, pred, np.zeros(len(y), dtype=int))
    return float(_f1(c.sum(0)))


def pooled_metrics(y, pred):
    c = group_counts(y, pred, np.zeros(len(y), dtype=int))[1].sum(0)
    div = lambda a, b: float(a / b) if b else 0.0
    out = {"n_reps": len(y), "n_bad": int(np.sum(y == BAD)), "macro_f1": float(_f1(c))}
    for name, k in (("bad", BAD), ("good", GOOD)):
        tp, fp, fn = c[k]
        out[name] = {
            "precision": div(tp, tp + fp),
            "recall": div(tp, tp + fn),
            "f1": div(2 * tp, 2 * tp + fp + fn),
        }
    out["balanced_accuracy"] = (out["bad"]["recall"] + out["good"]["recall"]) / 2
    return out


def paired_cluster_bootstrap(
    y, pred_a, pred_b, groups, n_boot=10000, seed=0, ci=0.95, exact_max=200_000
):
    ids, ca = group_counts(y, pred_a, groups)
    _, cb = group_counts(y, pred_b, groups)
    G = len(ids)
    if G**G <= exact_max:
        idx, mode = (
            np.array(list(itertools.product(range(G), repeat=G))),
            "exact_enumeration",
        )
    else:
        idx, mode = (
            np.random.default_rng(seed).integers(0, G, size=(n_boot, G)),
            "random",
        )
    ra, rb = ca[idx].sum(axis=1), cb[idx].sum(axis=1)
    support = lambda r, k: r[:, k, 0] + r[:, k, 2]
    valid = (support(ra, BAD) > 0) & (support(ra, GOOD) > 0)
    d = (_f1(rb) - _f1(ra))[valid]
    lo, hi = np.percentile(d, [50 * (1 - ci), 50 * (1 + ci)])
    return {
        "mode": mode,
        "n_resamples": len(idx),
        "n_valid": int(valid.sum()),
        "point_delta": float(_f1(cb.sum(0)) - _f1(ca.sum(0))),
        "delta_ci": [float(lo), float(hi)],
        "ci_level": ci,
        "share_delta_gt_0": float((d > 0).mean()),
        "share_delta_lt_0": float((d < 0).mean()),
        "n_participants": G,
    }


def jackknife_delta(y, pred_a, pred_b, groups):
    ids, ca = group_counts(y, pred_a, groups)
    _, cb = group_counts(y, pred_b, groups)
    ta, tb = ca.sum(0), cb.sum(0)
    full = float(_f1(tb) - _f1(ta))
    per = {str(g): float(_f1(tb - cb[i]) - _f1(ta - ca[i])) for i, g in enumerate(ids)}
    return {
        "full_delta": full,
        "without_participant": per,
        "min": min(per.values()),
        "max": max(per.values()),
        "sign_flips": [g for g, v in per.items() if np.sign(v) != np.sign(full)],
    }


def per_participant_table(y, pred_a, pred_b, groups):
    ids, _ = group_counts(y, pred_a, groups)
    groups = np.asarray(groups)
    rows = []
    for g in ids:
        m = groups == g
        rows.append(
            {
                "participant": str(g),
                "n_reps": int(m.sum()),
                "n_bad": int(np.sum(y[m] == BAD)),
                "a_correct": int(np.sum(pred_a[m] == y[m])),
                "b_correct": int(np.sum(pred_b[m] == y[m])),
            }
        )
    return rows


def tune_threshold(score, y, grid):
    return max(grid, key=lambda t: (macro_f1(y, np.where(score > t, BAD, GOOD)), -t))


def rule_lopo(score, y, folds, grid=None, fixed=None):
    if fixed is None and grid is None:
        raise ValueError("Provide a fixed threshold or a tuning grid.")
    pred, taus = np.full(len(y), -1), {}
    for f in folds:
        tr, te = np.asarray(f["train_idx"]), np.asarray(f["test_idx"])
        tau = fixed if fixed is not None else tune_threshold(score[tr], y[tr], grid)
        pred[te] = np.where(score[te] > tau, BAD, GOOD)
        taus[str(f["group"])] = float(tau)
    evaluated = np.flatnonzero(pred >= 0)
    return evaluated, pred[evaluated], taus
