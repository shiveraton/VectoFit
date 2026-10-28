from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from ..models import ModelRegistry, TrainingJob


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
            feature_selection=[
                "hip_angle",
                "knee_angle",
                "rom",
            ],
            random_seed=42,
            sample_count=10,
            train_count=7,
            test_count=3,
            status=TrainingJob.Status.COMPLETED,
            metrics={
                "accuracy": 0.9,
                "balanced_accuracy": 0.88,
                "precision": 0.91,
                "recall": 0.89,
                "f1": 0.90,
                "confusion_matrix": [
                    [1, 0],
                    [1, 1],
                ],
                "overall_class_distribution": {
                    "0": 3,
                    "1": 7,
                },
                "train_class_distribution": {
                    "0": 2,
                    "1": 5,
                },
                "test_class_distribution": {
                    "0": 1,
                    "1": 2,
                },
                "feature_importances": {
                    "hip_angle": 0.2,
                    "knee_angle": 0.7,
                    "rom": 0.1,
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

    def test_model_state_is_read_only_and_complete(self):
        response = self.client.get(f"/api/training/models/{self.model.pk}/state/")

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(response.data["id"], self.model.pk)

        self.assertEqual(response.data["training"]["job_id"], self.job.pk)
        self.assertEqual(response.data["view_angle"], "")
        self.assertEqual(response.data["prediction_target"], "binary_form")
        self.assertEqual(response.data["training_manifest"], {})

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
