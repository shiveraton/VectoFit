import numpy as np
from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import ValidationError

from .config import TASK_PROFILES, default_hyperparameters
from .serializers import TrainingJobRequestSerializer
from .services.data_loader import TrainingConfigurationError, group_split
from .services.trainer import (
    resolve_hyperparameters, scale_pos_weight, serialize_model, train_and_evaluate,
)
from .tests import make_sample_set


class TrainingConfigurationTests(SimpleTestCase):
    def test_defaults_and_locked_constants(self):
        self.assertEqual(default_hyperparameters(), {
            "n_estimators": 100, "learning_rate": 0.1, "max_depth": 2,
        })
        self.assertEqual(TASK_PROFILES["quality"], {
            "objective": "binary:logistic", "eval_metric": "logloss",
            "tree_method": "hist", "booster": "gbtree", "subsample": 1.0,
            "colsample_bytree": 1.0, "min_child_weight": 1, "reg_lambda": 1,
            "gamma": 0, "reg_alpha": 0, "seed": 42,
        })
        self.assertEqual(resolve_hyperparameters(), {
            **default_hyperparameters(), **TASK_PROFILES["quality"],
        })
        field = TrainingJobRequestSerializer().fields["hyperparameters"]
        self.assertEqual(field.get_default(), default_hyperparameters())
        self.assertEqual(TrainingJobRequestSerializer().validate_hyperparameters(
            {"max_depth": 3}), {**default_hyperparameters(), "max_depth": 3})

    def test_ranges_and_types(self):
        serializer = TrainingJobRequestSerializer()
        for name, values in {
            "n_estimators": [9, 501, 10.5, True, "100"],
            "learning_rate": [0.009, 0.301, float("nan"), float("inf"), False],
            "max_depth": [0, 7, 2.5, True],
        }.items():
            for value in values:
                with self.subTest(name=name, value=value), self.assertRaises(ValidationError):
                    serializer.validate_hyperparameters({name: value})
        for params in (
            {"n_estimators": 10, "learning_rate": 0.01, "max_depth": 1},
            {"n_estimators": 500, "learning_rate": 0.3, "max_depth": 6},
        ):
            self.assertEqual(serializer.validate_hyperparameters(params), params)

    def test_unknown_and_locked_keys_are_rejected(self):
        for name in [*TASK_PROFILES["quality"], "num_class", "scale_pos_weight", "random_state", "typo"]:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValidationError, "Unsupported or fixed"):
                    TrainingJobRequestSerializer().validate_hyperparameters({name: 1})
                with self.assertRaisesRegex(ValueError, "Unsupported or fixed"):
                    resolve_hyperparameters({name: 1})

    def test_removed_request_fields_are_rejected(self):
        for name in ("test_size", "random_seed", "seed", "split_strategy"):
            serializer = TrainingJobRequestSerializer(data={name: 1})
            self.assertFalse(serializer.is_valid())
            self.assertIn(name, serializer.errors)

    def test_fold_weights_and_repeatability(self):
        sample_set = make_sample_set()
        sample_set.labels[0] = 1
        first = train_and_evaluate(sample_set, {"n_estimators": 10})
        second = train_and_evaluate(sample_set, {"n_estimators": 10})
        self.assertEqual(first["metrics"], second["metrics"])
        self.assertEqual(serialize_model(first["model"]), serialize_model(second["model"]))
        self.assertEqual(first["folds"], second["folds"])
        self.assertEqual(len(first["folds"]), 4)
        self.assertEqual(len(first["metrics"]["oof_predictions"]), len(sample_set))
        self.assertEqual(scale_pos_weight(np.asarray([0, 0])), 1.0)
        weights = set()
        for fold in first["folds"]:
            training = [sample_set.labels[i] for i in fold["train_idx"]]
            expected = training.count(0) / training.count(1)
            self.assertEqual(fold["scale_pos_weight"], expected)
            weights.add(expected)
            train_groups = {sample_set.groups[i] for i in fold["train_idx"]}
            test_groups = {sample_set.groups[i] for i in fold["test_idx"]}
            self.assertFalse(train_groups & test_groups)
        self.assertGreater(len(weights), 1)

    def test_legacy_split_is_disabled_by_default_and_in_production(self):
        for debug, enabled in ((False, True), (True, False)):
            with override_settings(DEBUG=debug, TRAINING_ENABLE_LEGACY_SPLIT=enabled):
                with self.assertRaisesRegex(TrainingConfigurationError, "disabled"):
                    group_split(["a", "b"])

    def test_error_type_fold_with_missing_class_keeps_global_output_shape(self):
        sample_set = make_sample_set()
        sample_set.prediction_target = "error_type"
        sample_set.labels = ["correct_form", "shallow_depth"] * 8
        sample_set.labels[0] = "knee_valgus"
        result = train_and_evaluate(sample_set, {"n_estimators": 10})
        self.assertEqual(result["hyperparameters"]["objective"], "multi:softprob")
        self.assertEqual(result["hyperparameters"]["eval_metric"], "mlogloss")
        self.assertEqual(result["hyperparameters"]["num_class"], 3)
        self.assertEqual(result["task_profile"], "error_type")
        self.assertTrue(all("scale_pos_weight" not in fold for fold in result["folds"]))
        missing_class_fold = result["folds"][0]
        self.assertNotIn("knee_valgus", [sample_set.labels[i] for i in missing_class_fold["train_idx"]])
        probabilities = result["metrics"]["held_out_probabilities"]
        self.assertEqual(len(probabilities), len(sample_set))
        for row in probabilities:
            self.assertEqual(set(row), set(sample_set.labels))
            self.assertAlmostEqual(sum(row.values()), 1.0, places=6)
        self.assertEqual(np.asarray(result["metrics"]["confusion_matrix"]).shape, (3, 3))
        self.assertEqual(result["model"].predict_proba(np.asarray(sample_set.rows)).shape, (16, 3))

        repeat = train_and_evaluate(sample_set, {"n_estimators": 10})
        self.assertEqual(result["metrics"], repeat["metrics"])
        self.assertEqual(serialize_model(result["model"]), serialize_model(repeat["model"]))

    def test_error_type_manifest_records_profile_and_global_classes(self):
        from types import SimpleNamespace
        from .services.run_training_job import _build_manifest
        sample_set = make_sample_set()
        sample_set.prediction_target = "error_type"
        sample_set.labels = ["correct_form", "knee_valgus"] * 8
        sample_set.labels[0] = "shallow_depth"
        sample_set.sample_ids = list(range(len(sample_set)))
        sample_set.sample_metadata = [{"sample_id": i} for i in sample_set.sample_ids]
        result = train_and_evaluate(sample_set, {"n_estimators": 10})
        job = SimpleNamespace(pk=1, feature_schema_version="test", algorithm="xgboost")
        manifest = _build_manifest(job, [], sample_set, result, "diagonal", "error_type")
        self.assertEqual(manifest["task_profile"], "error_type")
        self.assertEqual(manifest["locked_hyperparameters"], {
            **TASK_PROFILES["error_type"], "num_class": 3,
        })
        self.assertEqual(manifest["user_hyperparameters"], {
            **default_hyperparameters(), "n_estimators": 10,
        })
        self.assertEqual(manifest["seed"], 42)
        self.assertEqual(manifest["xgboost_version"], manifest["environment"]["xgboost"])
        self.assertNotIn("final_scale_pos_weight", manifest)
        self.assertTrue(all("scale_pos_weight" not in fold for fold in manifest["folds"]))
        self.assertEqual(manifest["class_mapping"], {
            "0": "correct_form", "1": "knee_valgus", "2": "shallow_depth",
        })
