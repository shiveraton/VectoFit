import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import (
    InferenceRun,
    InferenceSimulation,
    InferenceStatus,
    ModelRegistry,
    TrainingJob,
)
from .services.inference_simulation import prepare_simulation
from .tasks import run_inference_task

BASE = "/api/training/inference-simulations/"


def repetitions():
    return [
        {
            "rep_number": 1,
            "start_ms": 0.0,
            "end_ms": 1000.0,
            "valid": True,
            "reason": None,
            "features": {"fppa_l_bottom": 5.0, "asym_bottom": 2.0, "asym_peak": 3.0},
        }
    ]


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class InferenceLabTests(APITestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        settings = override_settings(MEDIA_ROOT=directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        users = get_user_model()
        self.admin = users.objects.create_superuser(
            "lab-admin", "lab@example.com", "pass"
        )
        self.other = users.objects.create_superuser(
            "other-admin", "other@example.com", "pass"
        )
        self.client.force_authenticate(self.admin)
        self.models = []
        for index in range(2):
            job = TrainingJob.objects.create(
                status=TrainingJob.Status.COMPLETED,
                view_angle="frontal",
                prediction_target="knee_alignment",
                feature_schema_version="fppa_v2",
                feature_selection=["fppa_l_bottom"],
                training_manifest={"class_mapping": {"0": "bad", "1": "good"}},
            )
            model = ModelRegistry.objects.create(
                name="Lab test",
                version=str(index),
                training_job=job,
                algorithm="xgboost",
            )
            model.artifact.save(f"model-{index}.json", ContentFile(b"test artifact"))
            self.models.append(model)

    def create_simulation(self):
        with (
            patch("apps.training.tasks.run_inference_task.delay"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                BASE,
                {
                    "video_file": SimpleUploadedFile(
                        "squat.mp4", b"test video", "video/mp4"
                    ),
                    "model_id": self.models[0].pk,
                },
                format="multipart",
            )
        self.assertEqual(response.status_code, 202, response.data)
        return InferenceSimulation.objects.get(pk=response.data["id"])

    def test_upload_history_and_saved_video(self):
        simulation = self.create_simulation()
        self.assertEqual(simulation.creator, self.admin)
        self.assertEqual(simulation.runs.count(), 1)
        response = self.client.get(BASE)
        self.assertEqual(response.data["count"], 1)
        response = self.client.get(f"{BASE}{simulation.pk}/video/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"test video")
        response.close()
        detail = self.client.get(f"{BASE}{simulation.pk}/")
        self.assertEqual(
            detail.data["runs"][0]["model_snapshot"]["id"], self.models[0].pk
        )

    def test_access_is_admin_and_creator_scoped(self):
        simulation = self.create_simulation()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(BASE).data["count"], 0)
        for suffix in ("", "video/"):
            self.assertEqual(
                self.client.get(f"{BASE}{simulation.pk}/{suffix}").status_code, 404
            )
        user = get_user_model().objects.create_user(
            "viewer", "viewer@example.com", "pass"
        )
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(BASE).status_code, 403)

    def test_duplicate_run_and_busy_simulation(self):
        simulation = self.create_simulation()
        url = f"{BASE}{simulation.pk}/runs/"
        self.assertEqual(
            self.client.post(url, {"model_id": self.models[0].pk}).status_code, 200
        )
        self.assertEqual(simulation.runs.count(), 1)
        self.assertEqual(
            self.client.post(url, {"model_id": self.models[1].pk}).status_code, 409
        )
        self.assertEqual(self.client.delete(f"{BASE}{simulation.pk}/").status_code, 409)

    def test_queue_failure_can_be_retried(self):
        simulation = self.create_simulation()
        run = simulation.runs.get()
        from .inference_views import enqueue_inference

        with patch(
            "apps.training.tasks.run_inference_task.delay",
            side_effect=RuntimeError("offline"),
        ):
            enqueue_inference(run.pk)
        run.refresh_from_db()
        simulation.refresh_from_db()
        self.assertEqual(run.status, InferenceStatus.FAILED)
        self.assertEqual(simulation.status, InferenceStatus.FAILED)
        with (
            patch("apps.training.tasks.run_inference_task.delay"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                f"{BASE}{simulation.pk}/runs/", {"model_id": self.models[0].pk}
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(simulation.runs.count(), 1)
        run.refresh_from_db()
        self.assertEqual(run.status, InferenceStatus.PENDING)

    def test_incompatible_or_missing_model_artifact_is_rejected(self):
        model = self.models[0]
        model.training_job.view_angle = "sagittal"
        model.training_job.save()
        response = self.client.post(
            BASE,
            {
                "model_id": model.pk,
                "video_file": SimpleUploadedFile("test.mp4", b"test"),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(InferenceSimulation.objects.exists())
        model.training_job.view_angle = "frontal"
        model.training_job.save()
        model.artifact.delete()
        response = self.client.post(
            BASE,
            {
                "model_id": model.pk,
                "video_file": SimpleUploadedFile("test.mp4", b"test"),
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_model_comparison_reuses_prepared_features(self):
        simulation = self.create_simulation()
        prediction = {
            "status": "assessed",
            "predicted_class": "good",
            "probability": 0.8,
            "model_loading_ms": 2.0,
            "inference_ms": 1.0,
        }

        def prepare(item):
            item.repetitions = repetitions()
            item.feature_schema_version = "fppa_v2"
            item.status = InferenceStatus.COMPLETED
            item.save()

        with (
            patch(
                "apps.training.services.inference_simulation.prepare_simulation",
                side_effect=prepare,
            ) as preparation,
            patch(
                "apps.training.services.inference_simulation.predict_with_model",
                return_value=prediction,
            ) as predictor,
        ):
            first = simulation.runs.get()
            self.assertEqual(run_inference_task(first.pk), InferenceStatus.COMPLETED)
            second = InferenceRun.objects.create(
                simulation=simulation, model=self.models[1]
            )
            self.assertEqual(run_inference_task(second.pk), InferenceStatus.COMPLETED)
            preparation.assert_called_once()
            self.assertEqual(
                predictor.call_args_list[0].kwargs["features"],
                predictor.call_args_list[1].kwargs["features"],
            )
            run_inference_task(first.pk)
            self.assertEqual(predictor.call_count, 2)
        first.refresh_from_db()
        self.assertEqual(first.inference_ms, 1.0)
        self.assertFalse(self.models[0].is_active)

    def test_model_failure_preserves_prepared_features(self):
        simulation = self.create_simulation()
        simulation.status = InferenceStatus.COMPLETED
        simulation.repetitions = repetitions()
        simulation.feature_schema_version = "fppa_v2"
        simulation.save()
        with patch(
            "apps.training.services.inference_simulation.predict_with_model",
            side_effect=ValueError("bad artifact"),
        ):
            self.assertEqual(
                run_inference_task(simulation.runs.get().pk), InferenceStatus.FAILED
            )
        simulation.refresh_from_db()
        self.assertEqual(simulation.status, InferenceStatus.COMPLETED)
        self.assertEqual(simulation.repetitions, repetitions())

    def test_invalid_repetition_is_unavailable(self):
        simulation = self.create_simulation()
        simulation.status = InferenceStatus.COMPLETED
        simulation.repetitions = [
            {
                **repetitions()[0],
                "valid": False,
                "reason": "missing_pose",
                "features": {},
            }
        ]
        simulation.save()
        with patch(
            "apps.training.services.inference_simulation.predict_with_model"
        ) as predictor:
            run_inference_task(simulation.runs.get().pk)
            predictor.assert_not_called()
        run = simulation.runs.get()
        self.assertEqual(run.predictions[0]["status"], "not_assessed")

    def test_corrupt_video_marks_processing_failed(self):
        simulation = self.create_simulation()
        with patch(
            "apps.training.services.inference_simulation.cv2.VideoCapture"
        ) as capture:
            capture.return_value.isOpened.return_value = False
            capture.return_value.get.return_value = 0
            self.assertEqual(
                run_inference_task(simulation.runs.get().pk), InferenceStatus.FAILED
            )
        simulation.refresh_from_db()
        self.assertEqual(simulation.status, InferenceStatus.FAILED)

    def test_preparation_uses_processed_coordinate_system(self):
        simulation = self.create_simulation()
        capture = MagicMock()
        capture.get.side_effect = [30.0, 60.0]
        entries = [{"timestamp_ms": 0.0}, {"timestamp_ms": 1000.0}]
        processed = {
            "status": "success",
            "landmark_data": [],
            "sample_step": 2,
            "coordinate_width": 1280,
            "coordinate_height": 720,
            "native_fps": 60.0,
        }
        with (
            patch(
                "apps.training.services.inference_simulation.cv2.VideoCapture",
                return_value=capture,
            ),
            patch(
                "apps.training.services.inference_simulation.VideoProcessor.process_video",
                return_value=processed,
            ),
            patch(
                "apps.training.services.inference_simulation.collect_repetition_entries",
                return_value=[{"entries": entries}],
            ),
            patch(
                "apps.training.services.inference_simulation.extract_fppa_features",
                return_value=(repetitions()[0]["features"], {"valid": True}),
            ) as extract,
        ):
            prepare_simulation(simulation)
        self.assertEqual(extract.call_args.kwargs["frame_width"], 1280)
        self.assertEqual(extract.call_args.kwargs["sample_step"], 2)
        self.assertEqual(simulation.repetitions, repetitions())

    def test_delete_removes_video_and_runs(self):
        simulation = self.create_simulation()
        simulation.runs.update(status=InferenceStatus.FAILED)
        path = Path(simulation.video_file.path)
        self.assertTrue(path.exists())
        self.assertEqual(self.client.delete(f"{BASE}{simulation.pk}/").status_code, 204)
        self.assertFalse(path.exists())
        self.assertFalse(InferenceSimulation.objects.exists())
        self.assertFalse(InferenceRun.objects.exists())

    def test_public_media_url_does_not_expose_simulation_video(self):
        simulation = self.create_simulation()
        self.client.force_authenticate(None)
        response = self.client.get(simulation.video_file.url)
        self.assertEqual(response.status_code, 404)

    def test_oversized_upload_is_rejected(self):
        with patch("apps.training.inference_serializers.MAX_VIDEO_BYTES", 4):
            response = self.client.post(
                BASE,
                {
                    "model_id": self.models[0].pk,
                    "video_file": SimpleUploadedFile("large.mp4", b"12345"),
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(InferenceSimulation.objects.exists())

    def test_long_video_is_rejected_before_pose_processing(self):
        simulation = self.create_simulation()
        capture = MagicMock()
        capture.get.side_effect = [30.0, 30.0 * 301]
        with (
            patch(
                "apps.training.services.inference_simulation.cv2.VideoCapture",
                return_value=capture,
            ),
            patch(
                "apps.training.services.inference_simulation.VideoProcessor.process_video"
            ) as processor,
        ):
            self.assertEqual(
                run_inference_task(simulation.runs.get().pk), InferenceStatus.FAILED
            )
            processor.assert_not_called()

    def test_real_model_artifact_predicts_saved_features(self):
        from xgboost import XGBClassifier

        from .services.trainer import serialize_model

        simulation = self.create_simulation()
        simulation.status = InferenceStatus.COMPLETED
        simulation.feature_schema_version = "fppa_v2"
        simulation.repetitions = repetitions()
        simulation.save()
        model = self.models[0]
        estimator = XGBClassifier(n_estimators=2, max_depth=1, n_jobs=1)
        estimator.fit([[0.0], [1.0], [5.0], [6.0]], [0, 0, 1, 1])
        model.artifact.save("real-model.json", ContentFile(serialize_model(estimator)))
        run = simulation.runs.get()
        self.assertEqual(run_inference_task(run.pk), InferenceStatus.COMPLETED)
        run.refresh_from_db()
        self.assertIn(run.predictions[0]["predicted_class"], {"good", "bad"})
        self.assertGreaterEqual(run.inference_ms, 0.0)
        self.assertGreaterEqual(run.model_loading_ms, 0.0)

    def test_completed_simulation_accepts_another_model_through_api(self):
        simulation = self.create_simulation()
        simulation.status = InferenceStatus.COMPLETED
        simulation.repetitions = repetitions()
        simulation.save()
        simulation.runs.update(status=InferenceStatus.COMPLETED)
        with (
            patch("apps.training.tasks.run_inference_task.delay") as queued,
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                f"{BASE}{simulation.pk}/runs/", {"model_id": self.models[1].pk}
            )
        self.assertEqual(response.status_code, 202)
        queued.assert_called_once_with(response.data["id"])
        simulation.refresh_from_db()
        self.assertEqual(simulation.repetitions, repetitions())
        self.assertEqual(simulation.runs.count(), 2)

    def test_missing_pose_fails_without_manufactured_predictions(self):
        simulation = self.create_simulation()
        capture = MagicMock()
        capture.get.side_effect = [30.0, 60.0]
        with (
            patch(
                "apps.training.services.inference_simulation.cv2.VideoCapture",
                return_value=capture,
            ),
            patch(
                "apps.training.services.inference_simulation.VideoProcessor.process_video",
                return_value={
                    "status": "success",
                    "landmark_data": [],
                    "sample_step": 1,
                },
            ),
        ):
            self.assertEqual(
                run_inference_task(simulation.runs.get().pk), InferenceStatus.FAILED
            )
        run = simulation.runs.get()
        self.assertEqual(run.predictions, [])
        self.assertIn("No complete squat repetitions", run.error_message)
