import unittest
from unittest import mock

import numpy as np

from apps.analytics.services.features import M0_FEATURE_ORDER, M1_FEATURE_ORDER

from .services import evaluation
from .services.data_loader import (
    DatasetNotUsableError,
    InsufficientGroupsError,
    SampleSet,
    leave_one_participant_out_folds,
)
from .services.trainer import InsufficientDataError, train_and_evaluate

FAST = {"n_estimators": 20, "max_depth": 2, "learning_rate": 0.3}


def sample_set(rows, labels, groups, names, target="binary_form", hashes=None):
    return SampleSet(
        features=list(names),
        rows=rows,
        labels=labels,
        groups=groups,
        feature_names=list(names),
        warnings=[],
        errors=[],
        sample_ids=list(range(1, len(rows) + 1)),
        prediction_target=target,
        view_angle="frontal",
        pipeline_config_hashes=hashes or {"h": len(rows)},
    )


def separable(n_participants=6, reps=4, names=M1_FEATURE_ORDER):
    rows, labels, groups = [], [], []
    for participant in range(n_participants):
        for rep in range(reps):
            label = rep % 2
            rows.append([(1.0 if label else -1.0) + 0.01 * participant] * len(names))
            labels.append(label)
            groups.append(f"participant-{participant}")
    return sample_set(rows, labels, groups, names)


class FoldTests(unittest.TestCase):
    def test_one_fold_per_participant_partitioning_every_sample_once(self):
        groups = ["a", "a", "b", "b", "c", "c"]
        labels = [0, 1, 0, 1, 0, 1]
        folds, skipped = leave_one_participant_out_folds(groups, labels)
        self.assertEqual(skipped, [])
        self.assertEqual([fold["group"] for fold in folds], ["a", "b", "c"])
        held_out = sorted(i for fold in folds for i in fold["test_idx"])
        self.assertEqual(held_out, list(range(6)))

    def test_no_participant_appears_on_both_sides(self):
        groups = ["a", "a", "b", "b", "c", "c", "d", "d"]
        labels = [0, 1] * 4
        folds, _ = leave_one_participant_out_folds(groups, labels)
        for fold in folds:
            train = {groups[i] for i in fold["train_idx"]}
            test = {groups[i] for i in fold["test_idx"]}
            self.assertFalse(train & test)
            self.assertEqual(test, {fold["group"]})

    def test_participant_holding_the_only_sample_of_a_class_is_reported_as_skipped(
        self,
    ):
        groups = ["a", "a", "b", "b", "c", "c"]
        labels = [0, 1, 1, 1, 1, 1]
        folds, skipped = leave_one_participant_out_folds(groups, labels)
        self.assertEqual([fold["group"] for fold in folds], ["b", "c"])
        self.assertEqual(
            skipped, [{"group": "a", "reason": "training_split_missing_class"}]
        )

    def test_fewer_than_two_evaluable_participants_is_an_error(self):
        groups = ["a", "a", "b", "b"]
        labels = [0, 1, 1, 1]
        with self.assertRaisesRegex(InsufficientGroupsError, "Fewer than two"):
            leave_one_participant_out_folds(groups, labels)

    def test_requires_two_participants_and_aligned_inputs(self):
        with self.assertRaises(InsufficientGroupsError):
            leave_one_participant_out_folds(["a", "a"], [0, 1])
        with self.assertRaisesRegex(InsufficientGroupsError, "same number"):
            leave_one_participant_out_folds(["a", "b"], [0])

    def test_string_labels_for_error_type(self):
        groups = ["a", "a", "b", "b", "c", "c"]
        labels = ["correct_form", "knee_valgus"] * 3
        folds, skipped = leave_one_participant_out_folds(groups, labels)
        self.assertEqual((len(folds), skipped), (3, []))

    def test_folds_are_deterministic(self):
        groups = ["a", "a", "b", "b", "c", "c"]
        labels = [0, 1] * 3
        self.assertEqual(
            leave_one_participant_out_folds(groups, labels),
            leave_one_participant_out_folds(groups, labels),
        )


class LopoTrainerTests(unittest.TestCase):
    def test_pooled_out_of_fold_evaluation(self):
        data = separable()
        result = train_and_evaluate(data, FAST, seed=1)
        evaluation_block = result["evaluation"]
        self.assertEqual(evaluation_block["strategy"], "leave_one_participant_out")
        self.assertEqual(evaluation_block["n_folds"], 6)
        self.assertEqual(evaluation_block["evaluated_samples"], len(data))
        self.assertEqual(evaluation_block["unevaluated_samples"], 0)
        self.assertEqual(result["oof"]["index"], list(range(len(data))))
        self.assertEqual(result["train_idx"], list(range(len(data))))
        self.assertGreaterEqual(result["metrics"]["accuracy"], 0.9)
        self.assertIn("roc_auc", result["metrics"])
        self.assertEqual(
            set(evaluation_block["per_participant"]),
            {f"participant-{i}" for i in range(6)},
        )

    def test_deterministic_for_a_fixed_seed(self):
        data = separable()
        first = train_and_evaluate(data, FAST, seed=3)
        second = train_and_evaluate(data, FAST, seed=3)
        self.assertEqual(first["oof"]["predicted"], second["oof"]["predicted"])
        self.assertEqual(first["oof"]["probabilities"], second["oof"]["probabilities"])

    def test_held_out_scores_do_not_leak_participant_identity(self):
        rng = np.random.default_rng(0)
        rows, labels, groups = [], [], []
        for participant in range(14):
            label = int(rng.integers(0, 2))
            if participant == 0:
                label = 0
            if participant == 1:
                label = 1
            for _ in range(5):
                rows.append([float(participant)])
                labels.append(label)
                groups.append(f"p{participant}")
        data = sample_set(rows, labels, groups, ["fppa_l_bottom"])
        result = train_and_evaluate(data, {"n_estimators": 60, "max_depth": 4}, seed=0)
        final_in_sample = (
            result["model"].predict(np.asarray(rows)).astype(int) == np.asarray(labels)
        ).mean()
        self.assertEqual(final_in_sample, 1.0)
        self.assertLess(result["metrics"]["balanced_accuracy"], 0.8)

    def test_unevaluable_participant_is_counted_not_silently_dropped(self):
        groups = ["a"] * 2 + ["b"] * 2 + ["c"] * 2 + ["d"] * 2 + ["e"]
        labels = [0, 1, 0, 1, 0, 1, 1, 1, 0]
        rows = [[float(label)] for label in labels]
        data = sample_set(rows, labels, groups, ["fppa_l_bottom"])
        result = train_and_evaluate(data, FAST, seed=0)
        block = result["evaluation"]
        self.assertEqual(
            block["evaluated_samples"] + block["unevaluated_samples"], len(data)
        )
        self.assertEqual(
            block["n_participants"], block["n_folds"] + len(block["skipped_folds"])
        )

    def test_error_type_multiclass(self):
        names, rows, labels, groups = ["x"], [], [], []
        for participant in range(5):
            for index, target in enumerate(
                ("correct_form", "knee_valgus", "shallow_depth")
            ):
                rows.append([float(index)])
                labels.append(target)
                groups.append(f"p{participant}")
        data = sample_set(rows, labels, groups, names, target="error_type")
        result = train_and_evaluate(data, FAST, seed=0)
        self.assertEqual(len(result["metrics"]["confusion_matrix"]), 3)
        self.assertNotIn("roc_auc", result["metrics"])

    def test_single_participant_is_rejected(self):
        data = sample_set([[0.0], [1.0]], [0, 1], ["a", "a"], ["x"])
        with self.assertRaises(InsufficientGroupsError):
            train_and_evaluate(data, FAST)

    def test_holdout_remains_available_and_leak_free(self):
        data = separable()
        result = train_and_evaluate(
            data, FAST, seed=1, evaluation="holdout", test_size=0.34
        )
        self.assertEqual(result["evaluation"]["strategy"], "group_by_participant")
        train = {data.groups[i] for i in result["train_idx"]}
        test = {data.groups[i] for i in result["test_idx"]}
        self.assertFalse(train & test)

    def test_unknown_evaluation_strategy_is_rejected(self):
        with self.assertRaises(InsufficientDataError):
            train_and_evaluate(separable(), FAST, evaluation="kfold")


def informative_asymmetry_sets(n_participants=12, reps=6, seed=0):
    rng = np.random.default_rng(seed)
    rows1, rows0, labels, groups = [], [], [], []
    for participant in range(n_participants):
        for rep in range(reps):
            label = rep % 2
            noise = rng.normal(0, 1, 4).tolist()
            asym = [float(3 * (1 - label) + rng.normal(0, 0.2))] * 2
            rows0.append(noise)
            rows1.append(noise + asym)
            labels.append(label)
            groups.append(f"p{participant}")
    return (
        sample_set(rows0, labels, groups, M0_FEATURE_ORDER),
        sample_set(rows1, labels, groups, M1_FEATURE_ORDER),
    )


class PairedComparisonTests(unittest.TestCase):
    def test_informative_asymmetry_beats_noise_with_clustered_ci(self):
        m0, m1 = informative_asymmetry_sets()
        report = evaluation.paired_model_comparison(
            m0, m1, FAST, seed=0, n_bootstrap=300
        )
        self.assertEqual(report["n_participants"], 12)
        self.assertEqual(report["n_samples"], len(m0))
        self.assertGreater(report["delta"]["accuracy"], 0.2)
        low, high = report["bootstrap"]["accuracy_delta_ci95"]
        self.assertGreater(low, 0.0)
        self.assertGreaterEqual(high, low)
        self.assertEqual(report["bootstrap"]["method"], "participant_cluster_bootstrap")
        self.assertGreater(
            report["mcnemar"]["a_wrong_b_correct"],
            report["mcnemar"]["a_correct_b_wrong"],
        )
        self.assertEqual(report["b"]["features"], M1_FEATURE_ORDER)
        self.assertEqual(len(report["per_participant"]), 12)

    def test_identical_models_have_zero_delta_and_unit_p_value(self):
        data = separable()
        report = evaluation.paired_model_comparison(data, data, FAST, n_bootstrap=50)
        self.assertEqual(report["delta"]["accuracy"], 0.0)
        self.assertEqual(report["mcnemar"]["p_value_exact"], 1.0)
        self.assertEqual(report["bootstrap"]["accuracy_delta_ci95"], [0.0, 0.0])

    def test_unpaired_sample_sets_are_rejected(self):
        first, second = informative_asymmetry_sets()
        second.sample_ids = list(reversed(second.sample_ids))
        with self.assertRaises(ValueError):
            evaluation.paired_model_comparison(first, second, FAST)


class ReadinessReportTests(unittest.TestCase):
    def _build(self, data):
        return mock.patch.object(evaluation, "build_samples", return_value=data)

    def test_ready_when_lopo_viable_and_single_pipeline(self):
        data = separable()
        with self._build(data):
            report = evaluation.readiness_report([], "frontal")
        self.assertTrue(report["ok"])
        self.assertEqual(report["participants"], 6)
        self.assertTrue(report["lopo"]["viable"])
        self.assertIn("READY", evaluation.format_readiness_report(report))

    def test_mixed_pipeline_is_flagged_not_ready(self):
        data = separable()
        data.pipeline_config_hashes = {"old": 10, "new": 14}
        with self._build(data):
            report = evaluation.readiness_report([], "frontal")
        self.assertFalse(report["ok"])
        self.assertTrue(report["mixed_pipeline"])
        self.assertIn("MIXED", evaluation.format_readiness_report(report))

    def test_unusable_dataset_returns_reason_instead_of_raising(self):
        with mock.patch.object(
            evaluation, "build_samples", side_effect=DatasetNotUsableError("no reps")
        ):
            report = evaluation.readiness_report([], "frontal")
        self.assertFalse(report["ok"])
        self.assertEqual(report["reason"], "no reps")
        self.assertIn("NOT READY", evaluation.format_readiness_report(report))

    def test_single_participant_marks_lopo_not_viable(self):
        data = sample_set([[0.0], [1.0]], [0, 1], ["a", "a"], ["x"])
        with self._build(data):
            report = evaluation.readiness_report([], "frontal")
        self.assertFalse(report["ok"])
        self.assertFalse(report["lopo"]["viable"])


if __name__ == "__main__":
    unittest.main()
