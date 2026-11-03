import numpy as np
from django.test import SimpleTestCase
from sklearn.metrics import f1_score

from apps.training.services import lopo_evaluator as ev


class LopoEvaluatorTests(SimpleTestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.g = np.repeat([f"p{i}" for i in range(5)], 8)
        self.y = rng.integers(0, 2, 40)
        self.y[[0, 8]] = [0, 1]
        self.a = np.where(rng.random(40) < 0.7, self.y, 1 - self.y)
        self.b = np.where(rng.random(40) < 0.8, self.y, 1 - self.y)

    def test_macro_f1_matches_sklearn(self):
        self.assertAlmostEqual(
            ev.macro_f1(self.y, self.a),
            f1_score(self.y, self.a, average="macro", labels=[0, 1], zero_division=0),
        )

    def test_identical_predictions_give_zero_delta(self):
        b = ev.paired_cluster_bootstrap(self.y, self.a, self.a, self.g)
        self.assertEqual((b["point_delta"], b["delta_ci"]), (0.0, [0.0, 0.0]))
        self.assertEqual(b["mode"], "exact_enumeration")
        self.assertEqual(b["n_resamples"], 5**5)

    def test_jackknife_covers_every_participant(self):
        j = ev.jackknife_delta(self.y, self.a, self.b, self.g)
        self.assertEqual(set(j["without_participant"]), set(self.g))

    def test_rule_threshold_uses_training_fold_only(self):
        score = np.where(self.y == 0, 10.0, 1.0)
        folds = [
            {
                "group": g,
                "train_idx": np.flatnonzero(self.g != g),
                "test_idx": np.flatnonzero(self.g == g),
            }
            for g in sorted(set(self.g))
        ]
        idx, pred, taus = ev.rule_lopo(score, self.y, folds, grid=np.arange(0, 12, 0.5))
        self.assertEqual(len(idx), 40)
        self.assertEqual(ev.macro_f1(self.y[idx], pred), 1.0)
        self.assertEqual(set(taus), set(self.g))
