import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.analytics.services.features import FEATURE_ORDER, FEATURE_SCHEMA_VERSION
from apps.assessments.models import AssessmentSession, RepAssessment
from apps.datasets.models import (
    Dataset,
    DatasetSample,
    DatasetVideo,
    Participant,
    ViewAngle,
)
from apps.exercises.models import ExerciseVariant

from .models import ModelRegistry, TrainingJob
from .services.data_loader import (
    InsufficientGroupsError,
    SampleSet,
    build_samples,
    group_split,
)
from .services.run_training_job import run_training_job
from .services.trainer import InsufficientDataError, train_and_evaluate


def make_landmark_series():
    frame = {
        "left_shoulder": [100.0, 50.0],
        "right_shoulder": [120.0, 50.0],
        "left_hip": [100.0, 100.0],
        "right_hip": [120.0, 100.0],
        "left_knee": [100.0, 150.0],
        "right_knee": [120.0, 150.0],
        "left_ankle": [100.0, 200.0],
        "right_ankle": [120.0, 200.0],
    }
    return [frame.copy() for _ in range(12)]


User = get_user_model()
TEMP = tempfile.mkdtemp()


class GroupSplitTests(TestCase):
    def test_exact_search_finds_valid_partition_greedy_can_miss(self):
        groups = ["a", "b", "c", "d"]
        labels = [0, 1, 0, 1]
        train, test = group_split(groups, 0.5, labels=labels, seed=7, attempts=1)
        self.assertTrue(test in ([0, 1], [2, 3]) or test in ([0, 2], [1, 3]))
        self.assertEqual({labels[i] for i in train}, {0, 1})
        self.assertEqual({labels[i] for i in test}, {0, 1})
        self.assertFalse(set(groups[i] for i in train) & set(groups[i] for i in test))

    def test_class_with_one_participant_fails_with_coverage_diagnostic(self):
        with self.assertRaisesRegex(
            InsufficientGroupsError, "participant coverage"
        ) as ctx:
            group_split(["a", "a", "b", "b"], labels=["x", "x", "y", "y"])
        self.assertIn("'x': 1 participant", str(ctx.exception))

    def test_deterministic_and_isolated_for_multiclass_uneven_groups(self):
        groups = ["a"] * 5 + ["b"] + ["c"] * 3 + ["d"] * 2
        labels = (
            [
                "correct_form",
                "knee_valgus",
                "shallow_depth",
                "correct_form",
                "knee_valgus",
            ]
            + ["correct_form"]
            + ["knee_valgus", "shallow_depth", "correct_form"]
            + ["shallow_depth"] * 2
        )
        first = group_split(groups, 0.3, seed=11, labels=labels)
        second = group_split(groups, 0.3, seed=11, labels=labels)
        self.assertEqual(first, second)
        self.assertFalse(
            set(groups[i] for i in first[0]) & set(groups[i] for i in first[1])
        )

    def test_empty_mismatched_and_single_participant_inputs(self):
        with self.assertRaises(InsufficientGroupsError):
            group_split([])
        with self.assertRaisesRegex(InsufficientGroupsError, "same number"):
            group_split(["a", "b"], labels=[0])
        with self.assertRaisesRegex(InsufficientGroupsError, "only 1 participant"):
            group_split(["a", "a"], labels=[0, 1])


def make_sample_set():
    f_len = len(FEATURE_ORDER)
    rows, labels, groups = [], [], []
    for g in range(4):
        for lbl in (0, 1):
            for _ in range(2):
                rows.append([float(1.0 if lbl else -1.0)] * f_len)
                labels.append(lbl)
                groups.append(f"s-{g}")
    return SampleSet(
        features=list(FEATURE_ORDER),
        rows=rows,
        labels=labels,
        groups=groups,
        feature_names=list(FEATURE_ORDER),
        warnings=[],
        errors=[],
    )


class CorePipelineTests(TestCase):
    def test_split_and_xgboost_trainer(self):
        tr, te = group_split(
            ["a"] * 3 + ["b"] * 3 + ["c"] * 3 + ["d"] * 3,
            0.3,
            seed=1,
        )
        self.assertFalse(set(tr) & set(te))

        ss = make_sample_set()
        res = train_and_evaluate(
            ss,
            hyperparameters={
                "n_estimators": 30,
                "max_depth": 2,
                "learning_rate": 0.3,
                "subsample": 1.0,
                "colsample_bytree": 1.0,
            },
            seed=42,
        )
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

        cls.var = ExerciseVariant.objects.create(
            exercise_variant="squat",
            name="Squat",
            variant_type=ExerciseVariant.VariantType.BODYWEIGHT,
        )

        cls.dataset = Dataset.objects.create(
            name="D1",
            exercise_type="bodyweight_squat",
            purpose="training",
            status="READY",
        )

        cls.view_angle = ViewAngle.objects.create(angle_variant="diagonal")
        cls.frontal_view_angle = ViewAngle.objects.create(angle_variant="frontal")

        for group_index in range(4):
            participant = Participant.objects.create(
                participant_code=f"P{group_index + 1:03d}",
            )

            session = AssessmentSession.objects.create(
                user=cls.user,
                exercise_variant=cls.var,
                video_file="f.mp4",
            )

            for rep_number, is_correct in enumerate([True, False], 1):
                for angle, angle_suffix, rep_offset in (
                    (cls.view_angle, "diagonal", 0),
                    (cls.frontal_view_angle, "frontal", 10),
                ):
                    rep = RepAssessment.objects.create(
                        session=session,
                        rep_number=rep_number + rep_offset,
                        landmark_series=make_landmark_series(),
                    )
                    video = DatasetVideo.objects.create(
                        dataset=cls.dataset,
                        participant=participant,
                        view_angle=angle,
                        video_file=f"datasets/videos/test-{group_index}-{angle_suffix}-{rep_number}.mp4",
                        source_label=is_correct,
                        status=DatasetVideo.Status.READY,
                    )
                    DatasetSample.objects.create(
                        dataset=cls.dataset,
                        dataset_video=video,
                        rep_assessment=rep,
                        is_correct=is_correct,
                    )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP, ignore_errors=True)

    def test_dataset_serializer_exposes_angle_specific_counts(self):
        from apps.datasets.serializers import DatasetSerializer

        payload = DatasetSerializer(self.dataset).data
        self.assertEqual(payload["view_angles"], ["diagonal", "frontal"])
        self.assertEqual(payload["angle_training_stats"]["diagonal"]["sample_count"], 8)
        self.assertEqual(
            payload["angle_training_stats"]["diagonal"]["labelled_sample_count"], 8
        )
        self.assertEqual(payload["angle_training_stats"]["diagonal"]["good_count"], 4)
        self.assertEqual(payload["angle_training_stats"]["diagonal"]["bad_count"], 4)
        self.assertEqual(payload["angle_training_stats"]["frontal"]["sample_count"], 8)

    def test_zip_angle_selection_excludes_orphaned_legacy_sample(self):
        existing = self.dataset.samples.filter(
            dataset_video__view_angle=self.view_angle,
            is_correct=True,
        ).first()
        DatasetSample.objects.create(
            dataset=self.dataset,
            rep_assessment=existing.rep_assessment,
            is_correct=True,
        )

        samples = build_samples(
            [self.dataset], list(FEATURE_ORDER), view_angle="diagonal"
        )
        self.assertEqual(len(samples), 8)
        self.assertTrue(
            all(row["dataset_video_id"] is not None for row in samples.sample_metadata)
        )

    def test_error_type_training_supports_multiclass_metrics(self):
        feature_count = len(FEATURE_ORDER)
        rows, labels, groups = [], [], []
        for participant_index in range(6):
            for class_index, target in enumerate(
                ("correct_form", "knee_valgus", "shallow_depth")
            ):
                rows.append(
                    [float(class_index + participant_index / 10)] * feature_count
                )
                labels.append(target)
                groups.append(f"participant-{participant_index}")
        sample_set = SampleSet(
            features=list(FEATURE_ORDER),
            rows=rows,
            labels=labels,
            groups=groups,
            feature_names=list(FEATURE_ORDER),
            warnings=[],
            errors=[],
            prediction_target="error_type",
            view_angle="diagonal",
        )
        result = train_and_evaluate(
            sample_set,
            hyperparameters={"n_estimators": 5, "max_depth": 2},
            test_size=0.33,
            seed=7,
        )
        self.assertEqual(
            set(result["target_names"]),
            {"correct_form", "knee_valgus", "shallow_depth"},
        )
        self.assertEqual(len(result["metrics"]["confusion_matrix"]), 3)
        self.assertEqual(result["metrics"]["prediction_target"], "error_type")

    def test_build_samples_excludes_pending_review_samples(self):
        existing_sample = self.dataset.samples.first()

        pending_rep = RepAssessment.objects.create(
            session=existing_sample.rep_assessment.session,
            rep_number=99,
            landmark_series=make_landmark_series(),
        )

        DatasetSample.objects.create(
            dataset=self.dataset,
            dataset_video=existing_sample.dataset_video,
            rep_assessment=pending_rep,
            is_correct=None,
        )

        samples = build_samples(
            [self.dataset], list(FEATURE_ORDER), view_angle="diagonal"
        )

        self.assertEqual(len(samples), 8)
        self.assertEqual(len(samples.labels), 8)
        self.assertEqual(samples.labels.count(1), 4)
        self.assertEqual(samples.labels.count(0), 4)

    def test_build_samples_filters_to_selected_view_angle(self):
        samples = build_samples(
            [self.dataset], list(FEATURE_ORDER), view_angle="frontal"
        )
        self.assertEqual(len(samples), 8)
        self.assertTrue(
            all(item["view_angle"] == "frontal" for item in samples.sample_metadata)
        )
        self.assertTrue(
            all(
                item["dataset_video_id"] is not None for item in samples.sample_metadata
            )
        )

    def test_build_samples_keeps_legacy_single_video_support(self):
        participant = Participant.objects.create(participant_code="LEGACY-01")
        legacy_dataset = Dataset.objects.create(
            name="Legacy single-video dataset",
            exercise_type="bodyweight_squat",
            purpose="training",
            status="READY",
            participant=participant,
            view_angle=self.view_angle,
            video_file="datasets/videos/legacy.mp4",
        )
        session = AssessmentSession.objects.create(
            user=self.user,
            exercise_variant=self.var,
            video_file="datasets/videos/legacy.mp4",
        )
        for rep_number, is_correct in enumerate((True, False), start=1):
            rep = RepAssessment.objects.create(
                session=session,
                rep_number=rep_number,
                landmark_series=make_landmark_series(),
            )
            DatasetSample.objects.create(
                dataset=legacy_dataset,
                rep_assessment=rep,
                is_correct=is_correct,
            )

        samples = build_samples(
            [legacy_dataset], list(FEATURE_ORDER), view_angle="diagonal"
        )
        self.assertEqual(len(samples), 2)
        self.assertTrue(
            all(row["dataset_video_id"] is None for row in samples.sample_metadata)
        )
        self.assertEqual(set(samples.labels), {0, 1})

    def test_error_type_target_uses_specific_error_labels(self):
        self.dataset.samples.filter(
            dataset_video__view_angle=self.view_angle,
            is_correct=False,
        ).update(error_label="knee_valgus")
        samples = build_samples(
            [self.dataset],
            list(FEATURE_ORDER),
            view_angle="diagonal",
            prediction_target="error_type",
        )
        self.assertEqual(len(samples), 8)
        self.assertEqual(samples.labels.count("correct_form"), 4)
        self.assertEqual(samples.labels.count("knee_valgus"), 4)

    def test_error_type_excludes_reserved_correct_form_error_label(self):
        self.dataset.samples.filter(
            dataset_video__view_angle=self.view_angle,
            is_correct=False,
        ).update(error_label="correct_form")
        samples = build_samples(
            [self.dataset],
            list(FEATURE_ORDER),
            view_angle="diagonal",
            prediction_target="error_type",
        )
        self.assertEqual(len(samples), 4)
        self.assertEqual(set(samples.labels), {"correct_form"})
        self.assertTrue(any("reserved" in message for message in samples.errors))

    def test_training_request_rejects_single_class_binary_input(self):
        from .serializers import TrainingJobRequestSerializer

        DatasetSample.objects.filter(
            dataset=self.dataset,
            dataset_video__view_angle=self.view_angle,
            is_correct=False,
        ).update(is_correct=True)
        serializer = TrainingJobRequestSerializer(
            data={
                "dataset_ids": [self.dataset.pk],
                "view_angle": "diagonal",
                "prediction_target": "binary_form",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("prediction_target", serializer.errors)

    def test_training_request_rejects_evaluation_dataset(self):
        from .serializers import TrainingJobRequestSerializer

        self.dataset.purpose = "evaluation"
        self.dataset.save(update_fields=["purpose"])
        serializer = TrainingJobRequestSerializer(
            data={
                "dataset_ids": [self.dataset.pk],
                "view_angle": "diagonal",
                "prediction_target": "binary_form",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("dataset_ids", serializer.errors)

    @override_settings(MEDIA_ROOT=TEMP)
    def test_job_execution_lifecycle_and_api(self):
        job = TrainingJob.objects.create()
        run_training_job(
            job,
            dataset_ids=[self.dataset.pk],
            hyperparameters={"n_estimators": 5},
            view_angle="diagonal",
        )
        job.refresh_from_db()
        self.assertEqual(job.status, TrainingJob.Status.COMPLETED)
        self.assertTrue(bool(job.model_artifact))
        self.assertTrue(ModelRegistry.objects.filter(training_job=job).exists())
        self.assertEqual(len(job.training_manifest["samples"]), 8)
        self.assertEqual(job.training_manifest["view_angle"], "diagonal")
        self.assertTrue(
            all(
                sample["view_angle"] == "diagonal"
                for sample in job.training_manifest["samples"]
            )
        )
        self.assertTrue(
            all(
                "features" in sample
                and "source_label" in sample
                and "source_path" in sample
                for sample in job.training_manifest["samples"]
            )
        )
        self.assertRegex(job.training_manifest["manifest_sha256"], r"^[a-f0-9]{64}$")
        train_sample_ids = set(job.training_manifest["train_sample_ids"])
        test_sample_ids = set(job.training_manifest["test_sample_ids"])
        self.assertFalse(train_sample_ids & test_sample_ids)
        self.assertEqual(
            train_sample_ids | test_sample_ids,
            {sample["sample_id"] for sample in job.training_manifest["samples"]},
        )

        fail_job = TrainingJob.objects.create()
        run_training_job(fail_job, dataset_ids=[9999])
        fail_job.refresh_from_db()
        self.assertEqual(fail_job.status, TrainingJob.Status.FAILED)
        self.assertFalse(bool(fail_job.model_artifact))
        self.assertEqual(fail_job.training_manifest, {})

        self.client.force_authenticate(user=self.admin)
        url = reverse("training-job-create")
        res = self.client.post(
            url,
            {
                "dataset_ids": [self.dataset.pk],
                "view_angle": "diagonal",
                "prediction_target": "binary_form",
                "feature_selection": [
                    "hip_angle",
                    "knee_angle",
                    "rom",
                    "asymmetry",
                    "trunk_angle",
                    "velocity",
                ],
                "hyperparameters": {"n_estimators": 5},
                "test_size": 0.3,
                "random_seed": 42,
            },
            format="json",
        )

        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["view_angle"], "diagonal")
        self.assertEqual(res.data["sample_count"], 8)

        registry = ModelRegistry.objects.get(training_job_id=res.data["id"])
        activate_url = reverse("model-registry-activate", args=[registry.pk])
        activation = self.client.post(activate_url, {}, format="json")
        self.assertEqual(activation.status_code, 200, activation.data)
        registry.refresh_from_db()
        self.assertTrue(registry.is_active)

        state_url = reverse("model-state", args=[registry.pk])
        state = self.client.get(state_url)
        self.assertEqual(state.status_code, 200, state.data)
        self.assertEqual(state.data["view_angle"], "diagonal")
        self.assertEqual(state.data["prediction_target"], "binary_form")
        self.assertEqual(state.data["training"]["sample_count"], 8)
        self.assertTrue(state.data["artifact_available"])
        self.assertEqual(state.data["training_manifest"]["view_angle"], "diagonal")

        self.client.force_authenticate(user=self.user)
        predict_url = reverse("model-registry-predict")
        prediction = self.client.post(
            predict_url,
            {
                "model_name": registry.name,
                "view_angle": "diagonal",
                "prediction_target": "binary_form",
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "features": {name: 0.0 for name in FEATURE_ORDER},
            },
            format="json",
        )
        self.assertEqual(prediction.status_code, 200, prediction.data)
        self.assertIn("is_correct", prediction.data)
        self.assertIn("class_probabilities", prediction.data)
