from types import SimpleNamespace

import numpy as np
from django.test import SimpleTestCase

from .services.knee_baselines import choose_threshold, evaluate_baselines


class KneeBaselineTests(SimpleTestCase):
    def test_threshold_separates_training_classes(self):
        threshold = choose_threshold([1, 2, 8, 9], [1, 1, 0, 0])
        self.assertEqual(threshold, 2)
        np.testing.assert_array_equal(np.array([1, 2, 8, 9]) <= threshold, [1, 1, 0, 0])

    def test_held_out_labels_do_not_change_threshold_or_majority(self):
        samples = SimpleNamespace(
            feature_names=["fppa_l_peak", "fppa_r_peak"],
            rows=[[1, -2], [2, 1], [-8, 3], [9, 1], [50, -60]],
            labels=["good", "good", "bad", "bad", "bad"],
            sample_ids=list(range(5)),
        )
        folds = [{"participant": "held-out", "train_idx": [0, 1, 2, 3], "test_idx": [4]}]
        first = evaluate_baselines(samples, folds)
        samples.labels[-1] = "good"
        second = evaluate_baselines(samples, folds)
        self.assertEqual(first["folds"][0]["threshold_degrees"], 2)
        self.assertEqual(first["predictions"][0]["fppa_rule"], 0)
        for key in ("threshold_degrees", "majority_class"):
            self.assertEqual(first["folds"][0][key], second["folds"][0][key])

    def test_threshold_requires_both_training_classes(self):
        with self.assertRaises(ValueError):
            choose_threshold([1, 2], [1, 1])
