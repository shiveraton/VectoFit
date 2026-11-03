import shutil
import tempfile
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.analytics.services.features import (
    FEATURE_ORDER,
    FEATURE_SCHEMA_VERSION,
    M0_FEATURE_ORDER,
)
from apps.analytics.services.landmark_schema import LANDMARK_SCHEMA_VERSION
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
    DatasetNotUsableError,
    InsufficientGroupsError,
    SampleSet,
    TrainingConfigurationError,
    build_samples,
    group_split,
)
from .services.run_training_job import _build_manifest, run_training_job
from .services.trainer import InsufficientDataError, train_and_evaluate

FRAME_WIDTH, FRAME_HEIGHT = 640, 360
PIPELINE_HASH = "test-pipeline-hash"


def make_landmark_data(knee_in=0.0, n_frames=12, step_ms=1000.0 / 30.0):
    def point(x, y):
        return {"x": x, "y": y, "z": 0.0, "visibility": 0.99, "normalized": True}

    frames = []
    for index in range(n_frames):
        frames.append(
            {
                "frame_index": index,
                "timestamp_ms": index * step_ms,
                "landmarks": {
                    "left_shoulder": point(0.6, 0.15),
                    "right_shoulder": point(0.4, 0.15),
                    "left_hip": point(0.6, 0.4),
                    "right_hip": point(0.4, 0.4),
                    "left_knee": point(0.6 - knee_in, 0.6),
                    "right_knee": point(0.4 + knee_in, 0.6),
                    "left_ankle": point(0.6, 0.85),
                    "right_ankle": point(0.4, 0.85),
                },
            }
        )
    return {"schema_version": LANDMARK_SCHEMA_VERSION, "frames": frames}


def make_rep_kwargs(knee_in=0.0):
    return {
        "landmark_series": [],
        "landmark_data": make_landmark_data(knee_in),
        "landmark_schema_version": LANDMARK_SCHEMA_VERSION,
        "pipeline_config_hash": PIPELINE_HASH,
    }


class LabelSnapshotManifestTests(TestCase):
    def test_label_snapshot_hash_is_stable_and_tracks_label_changes(self):
        class Samples:
            def __init__(self):
                self.sample_ids = [3]
                self.sample_metadata = [
                    {"sample_id": 3, "is_correct": True, "label_source": "consensus"}
                ]
                self.rows = [[1.0]]
                self.feature_names = ["feature"]
                self.warnings = []
                self.errors = []
                self.model_version = "M1"
                self.exclusion_counts = {}
                self.pipeline_config_hashes = {}

            def __len__(self):
                return len(self.sample_ids)

        samples = Samples()
        args = (
            SimpleNamespace(pk=1, algorithm="test"),
            [SimpleNamespace(pk=2, name="dataset", purpose="training")],
            samples,
            {
                "train_idx": [0],
                "test_idx": [],
                "hyperparameters": {},
                "class_mapping": {},
                "target_names": [],
                "metrics": {},
                "evaluation": {"strategy": "group_by_participant"},
            },
            "frontal",
            "binary_form",
            0.3,
            42,
        )
        first = _build_manifest(*args)
        second = _build_manifest(*args)
        self.assertEqual(first["label_snapshot"], [[3, 1, "consensus"]])
        self.assertEqual(
            first["label_snapshot_sha256"], second["label_snapshot_sha256"]
        )
        samples.sample_metadata[0]["is_correct"] = False
        changed = _build_manifest(*args)
        self.assertNotEqual(
            first["label_snapshot_sha256"], changed["label_snapshot_sha256"]
        )


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


FAST_HYPERPARAMETERS = {
    "n_estimators": 30,
    "max_depth": 2,
    "learning_rate": 0.3,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
}


class CorePipelineTests(TestCase):
    def test_split_and_xgboost_trainer(self):
        tr, te = group_split(
            ["a"] * 3 + ["b"] * 3 + ["c"] * 3 + ["d"] * 3,
            0.3,
            seed=1,
        )
        self.assertFalse(set(tr) & set(te))

        ss = make_sample_set()
        res = train_and_evaluate(ss, hyperparameters=FAST_HYPERPARAMETERS, seed=42)
        self.assertIn("accuracy", res["metrics"])
        self.assertGreaterEqual(res["metrics"]["accuracy"], 0.8)
        self.assertEqual(res["evaluation"]["strategy"], "leave_one_participant_out")
        self.assertEqual(res["evaluation"]["n_folds"], 4)
        self.assertEqual(res["train_idx"], list(range(len(ss))))
        self.assertEqual(res["test_idx"], list(range(len(ss))))

        ss.labels = [1] * len(ss.labels)
        with self.assertRaises(InsufficientDataError):
            train_and_evaluate(ss)

    def test_holdout_strategy_is_still_available(self):
        ss = make_sample_set()
        res = train_and_evaluate(
            ss,
            hyperparameters=FAST_HYPERPARAMETERS,
            seed=42,
            evaluation="holdout",
            test_size=0.5,
        )
        self.assertEqual(res["evaluation"]["strategy"], "group_by_participant")
        self.assertFalse(set(res["train_idx"]) & set(res["test_idx"]))
        self.assertGreaterEqual(res["metrics"]["accuracy"], 0.8)


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
                processed_frame_width=FRAME_WIDTH,
                processed_frame_height=FRAME_HEIGHT,
            )

            for rep_number, is_correct in enumerate([True, False], 1):
                for angle, angle_suffix, rep_offset in (
                    (cls.view_angle, "diagonal", 0),
                    (cls.frontal_view_angle, "frontal", 10),
                ):
                    rep = RepAssessment.objects.create(
                        session=session,
                        rep_number=rep_number + rep_offset,
                        **make_rep_kwargs(knee_in=0.0 if is_correct else 0.06),
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

    def test_consensus_label_source_is_preserved_as_human_training_metadata(self):
        sample = self.dataset.samples.filter(
            dataset_video__view_angle=self.view_angle,
            is_correct=True,
        ).first()
        sample.label_source = "consensus"
        sample.save(update_fields=["label_source"])
        samples = build_samples(
            [self.dataset], list(FEATURE_ORDER), view_angle="diagonal"
        )
        metadata = next(
            row for row in samples.sample_metadata if row["sample_id"] == sample.pk
        )
        self.assertEqual(metadata["label_source"], "consensus")
        self.assertEqual(metadata["label_origin"], "human")

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
        self.assertEqual(result["evaluation"]["strategy"], "leave_one_participant_out")

    def test_build_samples_excludes_pending_review_samples(self):
        existing_sample = self.dataset.samples.first()

        pending_rep = RepAssessment.objects.create(
            session=existing_sample.rep_assessment.session,
            rep_number=99,
            **make_rep_kwargs(),
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
            processed_frame_width=FRAME_WIDTH,
            processed_frame_height=FRAME_HEIGHT,
        )
        for rep_number, is_correct in enumerate((True, False), start=1):
            rep = RepAssessment.objects.create(
                session=session,
                rep_number=rep_number,
                **make_rep_kwargs(knee_in=0.0 if is_correct else 0.06),
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
        with self.assertRaises(DatasetNotUsableError) as error:
            build_samples(
                [self.dataset],
                list(FEATURE_ORDER),
                view_angle="diagonal",
                prediction_target="error_type",
            )
        self.assertIn("'correct_form' is reserved", str(error.exception))

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

    def test_training_job_schema_default_tracks_the_extraction_schema(self):
        self.assertEqual(
            TrainingJob._meta.get_field("feature_schema_version").default,
            FEATURE_SCHEMA_VERSION,
        )

    def test_build_samples_refuses_mixed_pipeline_hashes(self):
        rep = (
            self.dataset.samples.filter(dataset_video__view_angle=self.view_angle)
            .first()
            .rep_assessment
        )
        RepAssessment.objects.filter(pk=rep.pk).update(pipeline_config_hash="other")
        with self.assertRaisesRegex(
            TrainingConfigurationError, "different preprocessing pipelines"
        ):
            build_samples([self.dataset], list(FEATURE_ORDER), view_angle="diagonal")
        samples = build_samples(
            [self.dataset],
            list(FEATURE_ORDER),
            view_angle="diagonal",
            allow_mixed_pipeline=True,
        )
        self.assertEqual(len(samples), 8)
        self.assertEqual(samples.pipeline_config_hashes, {PIPELINE_HASH: 7, "other": 1})

    def test_reps_without_landmarks_v2_are_excluded_and_counted(self):
        existing = self.dataset.samples.filter(
            dataset_video__view_angle=self.view_angle
        ).first()
        legacy_rep = RepAssessment.objects.create(
            session=existing.rep_assessment.session,
            rep_number=98,
            landmark_series=[],
        )
        DatasetSample.objects.create(
            dataset=self.dataset,
            dataset_video=existing.dataset_video,
            rep_assessment=legacy_rep,
            is_correct=True,
        )
        samples = build_samples(
            [self.dataset], list(FEATURE_ORDER), view_angle="diagonal"
        )
        self.assertEqual(len(samples), 8)
        self.assertEqual(sum(samples.exclusion_counts.values()), 1)
        self.assertTrue(any("sample" in message for message in samples.errors))

    def test_build_samples_rows_follow_the_model_version(self):
        m0 = build_samples(
            [self.dataset], None, view_angle="diagonal", model_version="M0"
        )
        m1 = build_samples(
            [self.dataset], None, view_angle="diagonal", model_version="M1"
        )
        self.assertEqual(m0.feature_names, M0_FEATURE_ORDER)
        self.assertEqual(m1.feature_names, list(FEATURE_ORDER))
        self.assertEqual(m0.sample_ids, m1.sample_ids)
        self.assertEqual(m0.groups, m1.groups)
        for row0, row1 in zip(m0.rows, m1.rows):
            self.assertEqual(row0, row1[: len(row0)])

    def test_build_samples_rejects_features_outside_the_model_version(self):
        with self.assertRaises(TrainingConfigurationError):
            build_samples(
                [self.dataset],
                ["asym_bottom"],
                view_angle="diagonal",
                model_version="M0",
            )

    def test_training_request_resolves_features_from_model_version(self):
        from .serializers import TrainingJobRequestSerializer

        payload = {
            "dataset_ids": [self.dataset.pk],
            "view_angle": "diagonal",
            "prediction_target": "binary_form",
        }
        for version, expected in (
            ("M0", M0_FEATURE_ORDER),
            ("M1", list(FEATURE_ORDER)),
        ):
            serializer = TrainingJobRequestSerializer(
                data={**payload, "model_version": version}
            )
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data["feature_selection"], expected)
            self.assertEqual(serializer.validated_data["evaluation"], "lopo")

        rejected = TrainingJobRequestSerializer(
            data={
                **payload,
                "model_version": "M0",
                "feature_selection": ["asym_bottom"],
            }
        )
        self.assertFalse(rejected.is_valid())
        self.assertIn("feature_selection", rejected.errors)

        legacy = TrainingJobRequestSerializer(
            data={**payload, "feature_selection": ["hip_angle", "knee_angle"]}
        )
        self.assertFalse(legacy.is_valid())
        self.assertIn("feature_selection", legacy.errors)

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
        manifest = job.training_manifest
        all_ids = {sample["sample_id"] for sample in manifest["samples"]}
        self.assertEqual(manifest["split_strategy"], "leave_one_participant_out")
        self.assertEqual(job.split_strategy, "leave_one_participant_out")
        self.assertEqual(manifest["model_version"], "M1")
        self.assertEqual(manifest["feature_schema_version"], FEATURE_SCHEMA_VERSION)
        self.assertEqual(job.feature_schema_version, FEATURE_SCHEMA_VERSION)
        self.assertEqual(job.feature_selection, list(FEATURE_ORDER))
        self.assertEqual(set(manifest["train_sample_ids"]), all_ids)
        self.assertEqual(set(manifest["test_sample_ids"]), all_ids)
        self.assertTrue(
            all(
                sample["split"] == "lopo_evaluated" and "out_of_fold" in sample
                for sample in manifest["samples"]
            )
        )
        self.assertEqual(manifest["evaluation"]["n_folds"], 4)
        self.assertEqual(manifest["exclusion_counts"], {})
        self.assertEqual(manifest["pipeline_config_hashes"], {PIPELINE_HASH: 8})

        holdout_job = TrainingJob.objects.create()
        run_training_job(
            holdout_job,
            dataset_ids=[self.dataset.pk],
            hyperparameters={"n_estimators": 5},
            view_angle="diagonal",
            evaluation="holdout",
        )
        holdout_job.refresh_from_db()
        self.assertEqual(holdout_job.status, TrainingJob.Status.COMPLETED)
        holdout_manifest = holdout_job.training_manifest
        self.assertEqual(holdout_manifest["split_strategy"], "group_by_participant")
        train_ids = set(holdout_manifest["train_sample_ids"])
        test_ids = set(holdout_manifest["test_sample_ids"])
        self.assertFalse(train_ids & test_ids)
        self.assertEqual(train_ids | test_ids, all_ids)

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
                "model_version": "M1",
                "hyperparameters": {"n_estimators": 5},
                "test_size": 0.3,
                "random_seed": 42,
            },
            format="json",
        )

        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["view_angle"], "diagonal")
        self.assertEqual(res.data["sample_count"], 8)
        self.assertEqual(res.data["split_strategy"], "leave_one_participant_out")
        self.assertEqual(res.data["feature_selection"], list(FEATURE_ORDER))
        self.assertEqual(res.data["feature_schema_version"], FEATURE_SCHEMA_VERSION)
        self.assertEqual(res.data["training_manifest_summary"]["model_version"], "M1")

        m0 = self.client.post(
            url,
            {
                "dataset_ids": [self.dataset.pk],
                "view_angle": "diagonal",
                "prediction_target": "binary_form",
                "model_version": "M0",
                "hyperparameters": {"n_estimators": 5},
                "random_seed": 42,
            },
            format="json",
        )
        self.assertEqual(m0.status_code, 201, m0.data)
        self.assertEqual(m0.data["feature_selection"], M0_FEATURE_ORDER)
        self.assertEqual(m0.data["training_manifest_summary"]["model_version"], "M0")

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
