from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from apps.training.models import TrainingJob
from apps.training.services.model_inference import (
    ModelInferenceError,
    _load_cached_model,
    predict_with_model,
)


class SelectedModelInferenceTests(SimpleTestCase):
    def setUp(self):
        self.estimator = Mock()
        self.estimator.predict.return_value = [1]
        self.estimator.predict_proba.return_value = [[0.2, 0.8]]

        artifact = MagicMock()
        artifact.name = "selected-model.json"
        artifact.size = 100
        self.modified_at = datetime(2026, 1, 1, tzinfo=UTC)
        artifact.storage.get_modified_time.return_value = self.modified_at

        job = SimpleNamespace(
            status=TrainingJob.Status.COMPLETED,
            prediction_target="knee_alignment",
            view_angle="frontal",
            feature_schema_version="fppa_v2",
            feature_selection=["fppa_r_peak", "fppa_l_bottom"],
            training_manifest={
                "class_mapping": {"0": "bad", "1": "good"},
            },
            metrics={},
        )

        self.model = SimpleNamespace(
            pk=123,
            name="Test model",
            version="1.0",
            is_active=False,
            artifact=artifact,
            training_job=job,
        )

    def test_inactive_model_uses_saved_feature_order(self):
        cache_key = (123, "selected-model.json", 100, self.modified_at)

        with patch.dict(
            "apps.training.services.model_inference._MODEL_CACHE",
            {cache_key: self.estimator},
            clear=True,
        ):
            result = predict_with_model(
                self.model,
                features={
                    "fppa_l_bottom": 5.0,
                    "fppa_r_peak": 12.0,
                },
                feature_schema_version="fppa_v2",
            )

        matrix = self.estimator.predict.call_args.args[0]

        self.assertEqual(matrix.tolist(), [[12.0, 5.0]])
        self.assertEqual(result["predicted_class"], "good")
        self.assertEqual(result["probability"], 0.8)
        self.assertEqual(result["model_loading_ms"], 0.0)
        self.assertGreaterEqual(result["inference_ms"], 0.0)
        self.assertFalse(self.model.is_active)

    def test_missing_feature_is_rejected(self):
        with self.assertRaises(ModelInferenceError) as error:
            predict_with_model(
                self.model,
                features={"fppa_l_bottom": 5.0},
                feature_schema_version="fppa_v2",
            )

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(
            error.exception.payload["missing_features"],
            ["fppa_r_peak"],
        )

    def test_missing_or_incomplete_class_mapping_is_rejected(self):
        cache_key = (123, "selected-model.json", 100, self.modified_at)
        for mapping in ({}, {"0": "bad"}, {"0": "bad", "1": ""}):
            with self.subTest(mapping=mapping):
                self.model.training_job.training_manifest = {"class_mapping": mapping}
                with (
                    patch.dict(
                        "apps.training.services.model_inference._MODEL_CACHE",
                        {cache_key: self.estimator},
                        clear=True,
                    ),
                    self.assertRaisesRegex(ModelInferenceError, "class mapping"),
                ):
                    predict_with_model(
                        self.model,
                        features={"fppa_l_bottom": 5.0, "fppa_r_peak": 12.0},
                        feature_schema_version="fppa_v2",
                    )

    def test_cache_loads_artifact_once(self):
        with (
            patch.dict(
                "apps.training.services.model_inference._MODEL_CACHE", {}, clear=True
            ),
            patch(
                "apps.training.services.model_inference.load_model",
                return_value=self.estimator,
            ) as loader,
        ):
            first, loading_ms = _load_cached_model(self.model)
            second, cached_ms = _load_cached_model(self.model)

        self.assertIs(first, self.estimator)
        self.assertIs(second, self.estimator)
        self.assertGreaterEqual(loading_ms, 0.0)
        self.assertEqual(cached_ms, 0.0)
        loader.assert_called_once()

    def test_cache_reloads_replaced_artifact(self):
        old_key = (123, "selected-model.json", 100, self.modified_at)
        artifact = self.model.artifact
        artifact.storage.get_modified_time.return_value = self.modified_at + timedelta(
            seconds=1
        )
        replacement = Mock()
        with (
            patch.dict(
                "apps.training.services.model_inference._MODEL_CACHE",
                {old_key: self.estimator},
                clear=True,
            ),
            patch(
                "apps.training.services.model_inference.load_model",
                return_value=replacement,
            ) as loader,
        ):
            estimator, _ = _load_cached_model(self.model)
        self.assertIs(estimator, replacement)
        loader.assert_called_once()

    def test_cache_evicts_oldest_model_when_full(self):
        cache = {("old", index): Mock() for index in range(8)}
        with patch.dict(
            "apps.training.services.model_inference._MODEL_CACHE",
            cache,
            clear=True,
        ):
            with patch(
                "apps.training.services.model_inference.load_model",
                return_value=self.estimator,
            ):
                _load_cached_model(self.model)
            from apps.training.services.model_inference import _MODEL_CACHE

            self.assertEqual(len(_MODEL_CACHE), 8)
            self.assertNotIn(("old", 0), _MODEL_CACHE)
