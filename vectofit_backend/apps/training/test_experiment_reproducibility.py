import json

import numpy as np
from django.test import SimpleTestCase

from apps.training.services.experiment_demo import synthetic_pair as make_pair
from apps.training.services.experiment_runner import run_from_sample_sets
from apps.training.services.trainer import BASELINE_HYPERPARAMETERS

CFG = {
    "experiment_id": "t",
    "seed": 42,
    "n_jobs": 1,
    "label_semantics": "synthetic",
    "decision_rule": "none",
    "uncertainty": {"n_boot": 200, "seed": 1, "ci": 0.95},
    "rule_baseline": {"grid": {"start": 0.0, "stop": 20.0, "step": 1.0}},
    "sensitivity": {"exclude_groups": ["demo-4"]},
}




class ExperimentReproducibilityTests(SimpleTestCase):
    def test_two_runs_are_byte_identical(self):
        a, _ = run_from_sample_sets(*make_pair(), CFG)
        b, _ = run_from_sample_sets(*make_pair(), CFG)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_models_share_baseline_hyperparameters_and_folds(self):
        res, oof = run_from_sample_sets(*make_pair(), CFG)
        self.assertEqual(
            res["hyperparameters_shared"],
            json.loads(json.dumps(BASELINE_HYPERPARAMETERS)),
        )
        self.assertEqual(res["main"]["lopo"]["n_folds"], 5)
        self.assertEqual(len(oof["sample_id"]), 40)

    def test_unknown_exclusion_group_rejected(self):
        with self.assertRaises(ValueError):
            run_from_sample_sets(
                *make_pair(),
                {**CFG, "sensitivity": {"exclude_groups": ["demo-99"]}},
            )
