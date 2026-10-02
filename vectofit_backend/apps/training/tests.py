import tempfile, shutil, numpy as np
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from apps.analytics.services.features import FEATURE_ORDER
from apps.assessments.models import AssessmentSession, RepAssessment
from apps.datasets.models import Dataset, DatasetSample
from apps.exercises.models import ExerciseVariant
from .models import ModelRegistry, TrainingJob
from .serializers import TrainingJobRequestSerializer
from .services import run_training_job
from .services.data_loader import SampleSet, build_samples, group_split
from .services.trainer import InsufficientDataError, train_and_evaluate

User = get_user_model()
TEMP = tempfile.mkdtemp()

def make_sample_set():
    f_len = len(FEATURE_ORDER)
    rows, labels, groups = [], [], []
    for g in range(4):
        for lbl in (0, 1):
            for _ in range(2):
                rows.append([float(1.0 if lbl else -1.0)] * f_len)
                labels.append(lbl)
                groups.append(f"s-{g}")
    return SampleSet(features=list(FEATURE_ORDER), rows=rows, labels=labels, groups=groups, feature_names=list(FEATURE_ORDER), warnings=[], errors=[])

class CorePipelineTests(TestCase):
    def test_split_and_xgboost_trainer(self):
        tr, te = group_split(["a"]*3 + ["b"]*3 + ["c"]*3 + ["d"]*3, 0.3, seed=1)
        self.assertFalse(set(tr) & set(te))
        ss = make_sample_set()
        res = train_and_evaluate(ss, hyperparameters={"n_estimators": 5}, seed=42)
        self.assertIn("accuracy", res["metrics"])
        self.assertGreaterEqual(res["metrics"]["accuracy"], 0.8)
        ss.labels = [1] * len(ss.labels)
        with self.assertRaises(InsufficientDataError):
            train_and_evaluate(ss)

class DBAndAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin", "a@e.com", "pass")
        cls.user = User.objects.create_user("u", "u@e.com", "pass")
        cls.var = ExerciseVariant.objects.create(exercise_variant="squat", name="Squat")
        cls.dataset = Dataset.objects.create(name="D1", exercise_type="bodyweight_squat")
        for _ in range(4):
            sess = AssessmentSession.objects.create(user=cls.user, exercise_variant=cls.var, video_file="f.mp4")
            for rep_i, is_c in enumerate([True, False], 1):
                frames = [{f"{s}_hip": [100.0, 200.0]} for s in ("left", "right")] * 12
                rep = RepAssessment.objects.create(session=sess, rep_number=rep_i, landmark_series=frames)
                DatasetSample.objects.create(dataset=cls.dataset, rep_assessment=rep, is_correct=is_c)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP, ignore_errors=True)

    def test_build_samples_and_serializer(self):
        ss = build_samples([self.dataset], list(FEATURE_ORDER))
        self.assertEqual(len(ss), 8)
        self.assertTrue(np.all(np.isfinite(np.asarray(ss.rows))))
        self.assertTrue(TrainingJobRequestSerializer(data={"dataset_ids": [self.dataset.pk]}).is_valid())
        self.assertFalse(TrainingJobRequestSerializer(data={"dataset_ids": [9999]}).is_valid())

    @override_settings(MEDIA_ROOT=TEMP)
    def test_job_execution_lifecycle_and_api(self):
        job = TrainingJob.objects.create()
        run_training_job(job, dataset_ids=[self.dataset.pk], hyperparameters={"n_estimators": 5})
        job.refresh_from_db()
        self.assertEqual(job.status, TrainingJob.Status.COMPLETED)
        self.assertTrue(bool(job.model_artifact))
        self.assertTrue(ModelRegistry.objects.filter(training_job=job).exists())

        fail_job = TrainingJob.objects.create()
        run_training_job(fail_job, dataset_ids=[9999])
        fail_job.refresh_from_db()
        self.assertEqual(fail_job.status, TrainingJob.Status.FAILED)

        self.client.force_authenticate(user=self.admin)
        res = self.client.post("/api/v1/training/start/", {"dataset_ids": [self.dataset.pk]}, format="json")
        self.assertIn(res.status_code, (200, 201))