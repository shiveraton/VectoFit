import numpy as np

from apps.analytics.services.features import FEATURE_ORDERS

from .data_loader import SampleSet


def synthetic_pair(seed=0):
    rng = np.random.default_rng(seed)
    rows, labels, groups = [], [], []
    for g in range(5):
        for r in range(8):
            bad = int((r < 3 and g != 4) or (g == 4 and r == 0))
            lb, rb = rng.normal(0, 2, 2) + (2 if bad else 0)
            lp, rp = rng.normal(0, 2, 2) + (9 if bad else 0)
            rows.append(
                {
                    "fppa_l_bottom": lb,
                    "fppa_r_bottom": rb,
                    "fppa_l_peak": lp,
                    "fppa_r_peak": rp,
                    "asym_bottom": abs(lb - rb),
                    "asym_peak": abs(lp - rp),
                }
            )
            labels.append(0 if bad else 1)
            groups.append(f"demo-{g}")
    meta = [
        {
            "sample_id": i,
            "is_correct": bool(label),
            "label_source": "",
            "label_origin": "synthetic",
        }
        for i, label in enumerate(labels)
    ]

    def build(version):
        names = list(FEATURE_ORDERS[version])
        return SampleSet(
            features=names,
            rows=[[row[n] for n in names] for row in rows],
            labels=list(labels),
            groups=list(groups),
            feature_names=names,
            warnings=[],
            errors=[],
            sample_ids=list(range(len(labels))),
            sample_metadata=meta,
            prediction_target="binary_form",
            view_angle="frontal",
            model_version=version,
        )

    return build("M0"), build("M1")
