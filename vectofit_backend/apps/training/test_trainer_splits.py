import numpy as np
from django.test import SimpleTestCase

from .models import TrainingJob
from .services.data_loader import SampleSet
from .services.trainer import InsufficientDataError, lopo_evaluate, train_and_evaluate


class TrainerSplitTests(SimpleTestCase):
    def make_samples(self):
        return SampleSet(
            features=["angle"],
            feature_names=["angle"],
            rows=[[-1.0], [1.0]] * 6,
            labels=["bad", "good"] * 6,
            groups=[participant for participant in range(6) for _ in range(2)],
            sample_ids=list(range(12)),
            warnings=[],
            errors=[],
            prediction_target="knee_alignment",
        )

    def test_holdout_uses_requested_participant_fraction(self):
        samples = self.make_samples()
        for fraction, test_count in ((0.15, 1), (0.3, 2), (0.5, 3)):
            with self.subTest(test_size=fraction):
                result = train_and_evaluate(
                    samples, {"n_estimators": 10}, test_size=fraction
                )
                metrics = result["metrics"]
                train_groups = {samples.groups[i] for i in result["train_idx"]}
                test_groups = {samples.groups[i] for i in result["test_idx"]}
                self.assertFalse(train_groups & test_groups)
                self.assertEqual(len(test_groups), test_count)
                self.assertEqual(metrics["evaluation_method"], "holdout")
                self.assertEqual(metrics["fold_count"], 1)
                self.assertEqual(metrics["test_participant_count"], test_count)
                self.assertEqual(metrics["train_participant_count"], 6 - test_count)
                self.assertEqual(np.sum(metrics["confusion_matrix"]), len(result["test_idx"]))
                self.assertEqual(len(metrics["held_out_probabilities"]), len(result["test_idx"]))
                self.assertNotIn("oof_predictions", metrics)

    def test_lopo_evaluates_each_participant_once(self):
        samples = self.make_samples()
        metrics = lopo_evaluate(samples, {"n_estimators": 10})
        self.assertEqual(metrics["evaluation_method"], TrainingJob.TrainingSplit.LOPO)
        self.assertEqual(metrics["fold_count"], 6)
        self.assertEqual(metrics["train_participant_count"], 5)
        self.assertEqual(metrics["test_participant_count"], 1)
        self.assertEqual(len(metrics["oof_predictions"]), len(samples))
        for fold in metrics["folds"]:
            train_groups = {samples.groups[i] for i in fold["train_idx"]}
            test_groups = {samples.groups[i] for i in fold["test_idx"]}
            self.assertFalse(train_groups & test_groups)
            self.assertEqual(len(test_groups), 1)

    def test_missing_training_class_is_still_rejected(self):
        samples = self.make_samples()
        samples.labels = ["bad"] * 12
        samples.labels[0] = "good"
        with self.assertRaisesRegex(InsufficientDataError, "leaves one class"):
            train_and_evaluate(
                samples, {"n_estimators": 10},
                split_strategy=TrainingJob.TrainingSplit.LOPO,
            )
