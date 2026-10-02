from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Dataset, DatasetSample

User = get_user_model()


class DatasetAPITests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password123"
        )
        self.regular_user = User.objects.create_user(
            username="user", email="user@example.com", password="password123"
        )

        self.dataset = Dataset.objects.create(
            name="Bench Press Form",
            description="Tracking bar path and velocity",
            exercise_type="Strength",
            purpose="Validation",
            primary_target="Pectorals",
        )
        self.list_url = reverse("dataset-list")

    def test_unauthenticated_user_denied_access(self):
        response = self.client.get(self.list_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_regular_user_denied_access(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_list_datasets(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_admin_user_can_create_dataset(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Squat Depth Dataset",
            "description": "3D pose estimation keypoints",
            "exercise_type": "Legs",
            "purpose": "Training",
            "primary_target": "Quadriceps",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Dataset.objects.count(), 2)