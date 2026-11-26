import numpy as np
from django.test import SimpleTestCase

from .services.source_evaluation import evaluate_splits, magnitude_features
from .services.trainer import resolve_hyperparameters


class SourceEvaluationTests(SimpleTestCase):
    names = ["fppa_l_peak", "fppa_r_peak", "fppa_l_bottom", "fppa_r_bottom", "asym_bottom", "asym_peak"]

    def test_magnitudes_use_both_sides_and_preserve_feature_order(self):
        result = magnitude_features([[-9, 2, 3, -4, -5, 6]], self.names)
        np.testing.assert_array_equal(result, [[9, 4, 5, 6]])

    def test_cross_source_evaluation_preserves_held_out_rows(self):
        rows = [[1, -2, 1, -1, 0, 1], [8, -9, 7, -8, 1, 1]] * 2
        result = evaluate_splits(
            rows, [1, 0, 1, 0], ["p1", "p1", "p2", "p2"], ["mdy", "mdy", "zen", "zen"],
            self.names, [("mdy_to_zen", [0, 1], [2, 3])],
            resolve_hyperparameters({"n_estimators": 10}, prediction_target="knee_alignment"),
        )
        self.assertEqual([r["index"] for r in result["predictions"]], [2, 3])
        self.assertEqual(set(result["by_source"]), {"zen"})
        self.assertEqual(result["folds"][0]["threshold_degrees"], 2)
        self.assertEqual(result["models"]["fppa_rule"]["bad_recall"], 1)
        self.assertEqual(result["models"]["fppa_rule"]["accuracy"], 1)

    def test_participant_overlap_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Participant leakage"):
            evaluate_splits(
                [[1, 2, 1, 2, 0, 0]] * 2, [0, 1], ["p1", "p1"], ["mdy", "zen"],
                self.names, [("invalid", [0], [1])], {},
            )
