from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.analytics.services.features import (
    FEATURE_ORDER,
    FEATURE_SCHEMA_VERSION,
    M0_FEATURE_ORDER,
)

from ..models import ModelRegistry, TrainingJob

LOPO = "leave_one_participant_out"


class ModelStateApiTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            username="model-state-admin",
            email="model-state-admin@example.com",
            password="test-password-123",
        )

        self.client = APIClient()

        self.client.force_authenticate(user=self.admin)

        self.job = TrainingJob.objects.create(
            view_angle="frontal",
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            split_strategy=LOPO,
            feature_selection=list(FEATURE_ORDER),
            random_seed=42,
            sample_count=10,
            train_count=10,
            test_count=10,
            status=TrainingJob.Status.COMPLETED,
            training_manifest={
                "manifest_version": 2,
                "model_version": "M1",
                "split_strategy": LOPO,
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "view_angle": "frontal",
                "exclusion_counts": {"shorter_than_filter_window": 2},
                "evaluation": {"strategy": LOPO, "n_folds": 5},
                "samples": [],
                "train_sample_ids": [],
                "test_sample_ids": [],
            },
            metrics={
                "accuracy": 0.9,
                "balanced_accuracy": 0.88,
                "precision": 0.91,
                "recall": 0.89,
                "f1": 0.90,
                "roc_auc": 0.95,
                "confusion_matrix": [
                    [1, 0],
                    [1, 1],
                ],
                "overall_class_distribution": {
                    "BAD_FORM": 3,
                    "GOOD_FORM": 7,
                },
                "train_class_distribution": {
                    "BAD_FORM": 3,
                    "GOOD_FORM": 7,
                },
                "test_class_distribution": {
                    "BAD_FORM": 3,
                    "GOOD_FORM": 7,
                },
                "feature_importances": {
                    "fppa_l_bottom": 0.2,
                    "fppa_r_bottom": 0.2,
                    "fppa_l_peak": 0.1,
                    "fppa_r_peak": 0.1,
                    "asym_bottom": 0.3,
                    "asym_peak": 0.1,
                },
            },
        )

        self.model = ModelRegistry.objects.create(
            name="vectofit-squat-classifier",
            version="1.0",
            training_job=self.job,
            algorithm=TrainingJob.Algorithm.XGBOOST,
            metrics=self.job.metrics,
            is_active=True,
        )

    def get_state(self, model=None):
        model = model or self.model
        return self.client.get(f"/api/training/models/{model.pk}/state/")

    def test_model_state_is_read_only_and_complete(self):
        response = self.get_state()

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(response.data["id"], self.model.pk)

        self.assertEqual(response.data["training"]["job_id"], self.job.pk)
        self.assertEqual(response.data["view_angle"], "frontal")
        self.assertEqual(response.data["prediction_target"], "binary_form")
        self.assertEqual(
            response.data["feature_schema_version"], FEATURE_SCHEMA_VERSION
        )

        self.assertEqual(
            response.data["features"]["selected"], self.job.feature_selection
        )

        self.assertEqual(
            response.data["evaluation"]["accuracy"],
            0.9,
        )

        self.assertEqual(
            response.data["evaluation"]["confusion_matrix"],
            [
                [1, 0],
                [1, 1],
            ],
        )

    def test_model_state_reports_the_evaluation_strategy_and_manifest(self):
        response = self.get_state()

        self.assertEqual(response.data["training"]["split_strategy"], LOPO)
        manifest = response.data["training_manifest"]
        self.assertEqual(manifest["model_version"], "M1")
        self.assertEqual(manifest["split_strategy"], LOPO)
        self.assertEqual(
            manifest["exclusion_counts"], {"shorter_than_filter_window": 2}
        )
        self.assertEqual(manifest["evaluation"]["n_folds"], 5)

    def test_m0_model_state_lists_only_fppa_features(self):
        m0_job = TrainingJob.objects.create(
            view_angle="frontal",
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            split_strategy=LOPO,
            feature_selection=list(M0_FEATURE_ORDER),
            status=TrainingJob.Status.COMPLETED,
            metrics={
                "accuracy": 0.8,
                "feature_importances": {name: 0.25 for name in M0_FEATURE_ORDER},
            },
        )
        m0_model = ModelRegistry.objects.create(
            name="vectofit-squat-classifier",
            version="1.1",
            training_job=m0_job,
            algorithm=TrainingJob.Algorithm.XGBOOST,
            metrics=m0_job.metrics,
        )

        response = self.get_state(m0_model)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["features"]["selected"], list(M0_FEATURE_ORDER))
        self.assertEqual(
            set(response.data["features"]["importances"]), set(M0_FEATURE_ORDER)
        )

    def test_legacy_model_without_manifest_still_serializes(self):
        legacy_job = TrainingJob.objects.create(
            feature_selection=["hip_angle", "knee_angle", "rom"],
            status=TrainingJob.Status.COMPLETED,
            metrics={"accuracy": 0.7},
        )
        legacy_model = ModelRegistry.objects.create(
            name="legacy",
            version="1.0",
            training_job=legacy_job,
            algorithm=TrainingJob.Algorithm.XGBOOST,
            metrics=legacy_job.metrics,
        )

        response = self.get_state(legacy_model)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["view_angle"], "")
        self.assertEqual(response.data["training_manifest"], {})
