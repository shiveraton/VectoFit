import json
import math
import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.analytics.services.features import FEATURE_ORDER, FEATURE_SCHEMA_VERSION
from apps.analytics.services.features import FeatureExtractionError
from apps.analytics.services.fppa import M1_FEATURES
from apps.assessments.models import AssessmentSession, RepAssessment
from apps.datasets.models import (
    Dataset,
    DatasetSample,
    DatasetVideo,
    Participant,
    ViewAngle,
)
from apps.datasets.models import KneeAnnotation
from apps.exercises.models import ExerciseVariant

from .models import ModelRegistry, TrainingJob
from .services.data_loader import (
    InsufficientGroupsError,
    DatasetNotUsableError,
    SampleSet,
    build_samples,
    group_split,
    _training_frame_rate,
)
from .services.run_training_job import run_training_job
from .services.trainer import InsufficientDataError, train_and_evaluate
from .services.trainer import lopo_evaluate


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
    return [
        {
            "landmarks": frame.copy(),
            "frame_index": index,
            "timestamp_ms": index * (1000.0 / 30.0),
            "native_fps": 30.0,
            "source_width": 1280,
            "source_height": 720,
        }
        for index in range(12)
    ]


User = get_user_model()
TEMP = tempfile.mkdtemp()


class PilotResultsViewTests(APITestCase):
    @override_settings(PILOT_RESULTS_PATH=TEMP + "/pilot-results.json")
    def test_admin_can_read_pilot_results_json(self):
        path = TEMP + "/pilot-results.json"
        os.makedirs(TEMP, exist_ok=True)
        with open(path, "w", encoding="utf-8") as result_file:
            json.dump({"label": "exploratory pilot", "M0": {"macro_f1": 0.5}}, result_file)
        admin = User.objects.create_superuser("pilot-admin", "pilot@example.com", "pass")
        self.client.force_authenticate(user=admin)

        response = self.client.get(reverse("pilot-results"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["label"], "exploratory pilot")


@override_settings(DEBUG=True, TRAINING_ENABLE_LEGACY_SPLIT=True)
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

    def test_large_pilot_uses_bounded_search_and_keeps_participants_separate(self):
        groups = [f"p{i}" for i in range(20) for _ in range(2)]
        labels = [0, 1] * 20
        with patch("apps.training.services.data_loader.combinations", side_effect=AssertionError("unbounded search")):
            first = group_split(groups, labels=labels, seed=7, attempts=8)
            self.assertEqual(first, group_split(groups, labels=labels, seed=7, attempts=8))
        train, test = first
        self.assertFalse({groups[i] for i in train} & {groups[i] for i in test})
        self.assertEqual({labels[i] for i in test}, {0, 1})


class TrainingTimingTests(TestCase):
    def test_source_video_fps_is_adjusted_for_the_30fps_sampling_step(self):
        sample = SimpleNamespace(
            rep_assessment=SimpleNamespace(
                landmark_series=[],
                session=SimpleNamespace(video_file=None),
            ),
            dataset_video_id=None,
            dataset_video=None,
        )
        dataset = SimpleNamespace(video_file=SimpleNamespace(path="sample.mp4"))
        capture = SimpleNamespace(
            get=lambda _property: 60.0,
            release=lambda: None,
        )
        with patch("apps.training.services.data_loader.cv2.VideoCapture", return_value=capture):
            fps, source = _training_frame_rate(sample, dataset)

        self.assertTrue(math.isclose(fps, 30.0))
        self.assertEqual(source, "source_video_fps_sampled_at_30fps")

    def test_missing_timing_metadata_and_video_fails_closed(self):
        sample = SimpleNamespace(
            rep_assessment=SimpleNamespace(
                landmark_series=[],
                session=SimpleNamespace(video_file=None),
            ),
            dataset_video_id=None,
            dataset_video=None,
        )
        dataset = SimpleNamespace(video_file=None)

        with self.assertRaisesRegex(FeatureExtractionError, "No usable frame timestamps"):
            _training_frame_rate(sample, dataset)


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
        ss = make_sample_set()
        res = train_and_evaluate(
            ss,
            hyperparameters={
                "n_estimators": 30,
                "max_depth": 2,
                "learning_rate": 0.3,
            },
        )
        self.assertIn("accuracy", res["metrics"])
        self.assertGreaterEqual(res["metrics"]["accuracy"], 0.8)

        ss.labels = [1] * len(ss.labels)
        with self.assertRaises(InsufficientDataError):
            train_and_evaluate(ss)

    def test_lopo_reports_macro_f1_for_each_participant(self):
        sample_set = SampleSet(
            rows=[[float(label), float(label)] for label in (0, 1) * 4],
            labels=["bad", "good"] * 4,
            groups=[f"participant-{index}" for index in range(4) for _ in (0, 1)],
            features=["fppa_l_bottom", "fppa_r_bottom"],
            feature_names=["fppa_l_bottom", "fppa_r_bottom"],
            warnings=[],
            errors=[],
            prediction_target="knee_alignment",
        )

        result = lopo_evaluate(
            sample_set,
            hyperparameters={"n_estimators": 10, "max_depth": 2},
        )

        self.assertIn("macro_f1", result)
        self.assertEqual(len(result["per_participant"]), 4)


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
        result = train_and_evaluate(sample_set, hyperparameters={"n_estimators": 10})
        self.assertEqual(len(result["metrics"]["confusion_matrix"]), 3)
        self.assertEqual(result["hyperparameters"]["num_class"], 3)
        self.assertEqual(result["task_profile"], "error_type")
        self.assertTrue(all("scale_pos_weight" not in fold for fold in result["folds"]))

    def annotate_frontal_samples(self):
        for sample in self.dataset.samples.filter(dataset_video__view_angle=self.frontal_view_angle):
            KneeAnnotation.objects.create(
                sample=sample, annotator=self.admin,
                annotation={
                    "left": {"grade": "aligned" if sample.is_correct else "deviated", "direction": "uncertain"},
                    "right": {"grade": "aligned", "direction": "none"},
                    "notes": "",
                },
            )

    def test_pilot_command_records_shared_cohort_and_model_configuration(self):
        from django.core.management import call_command
        from .management.commands import run_m0_m1
        self.annotate_frontal_samples()
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "pilot.json")
            with patch.object(run_m0_m1, "BOOTSTRAP_ITERATIONS", 10):
                call_command("run_m0_m1", dataset_ids=[self.dataset.pk], output=path)
            with open(path, encoding="utf-8") as artifact:
                result = json.load(artifact)
        self.assertEqual(result["evaluation_method"], "leave_one_participant_out")
        self.assertEqual(len(result["samples"]), 8)
        self.assertEqual(len(result["M0_features"]), 4)
        self.assertEqual(len(result["M1_features"]), 6)
        self.assertEqual(result["M0"]["hyperparameters"], result["M1"]["hyperparameters"])
        self.assertEqual(
            [row["sample_id"] for row in result["M0"]["oof_predictions"]],
            [row["sample_id"] for row in result["M1"]["oof_predictions"]],
        )
        self.assertTrue(all(len(row["features"]) == 6 and row["knee_annotations"] for row in result["samples"]))
        self.assertIn("xgboost", result["environment"])

    def test_m1_request_enforces_frontal_view_and_complete_ordered_schema(self):
        from .serializers import TrainingJobRequestSerializer
        self.annotate_frontal_samples()
        payload = {
            "dataset_ids": [self.dataset.pk],
            "view_angle": "frontal", "prediction_target": "knee_alignment",
        }
        for changes, field in (({"view_angle": "diagonal"}, "view_angle"),
                               ({"feature_selection": list(M1_FEATURES[:4])}, "feature_selection")):
            serializer = TrainingJobRequestSerializer(data={**payload, **changes})
            self.assertFalse(serializer.is_valid())
            self.assertIn(field, serializer.errors)
        serializer = TrainingJobRequestSerializer(data={**payload, "feature_selection": list(reversed(M1_FEATURES))})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["feature_selection"], list(M1_FEATURES))

    @override_settings(MEDIA_ROOT=TEMP)
    def test_new_knee_annotations_support_m1_activation_and_pilot_loading(self):
        from .management.commands.run_m0_m1 import _load_samples
        from .services.model_card import build_model_card
        self.annotate_frontal_samples()
        sample_set = _load_samples([self.dataset.pk], 1280, 720)
        self.assertEqual(len(sample_set), 8)
        self.assertTrue(all(row["label_origin"] == "human" for row in sample_set.sample_metadata))
        self.assertTrue(all(row["knee_annotations"][0]["rubric_version"] == "knee_v1" for row in sample_set.sample_metadata))
        job = TrainingJob.objects.create(view_angle="frontal", prediction_target="knee_alignment")
        run_training_job(job, dataset_ids=[self.dataset.pk], view_angle="frontal",
                         prediction_target="knee_alignment", hyperparameters={"n_estimators": 10})
        self.assertEqual(job.status, TrainingJob.Status.COMPLETED, job.error_message)
        self.assertEqual(set(job.training_manifest["train_sample_ids"] + job.training_manifest["test_sample_ids"]), set(sample_set.sample_ids))
        self.assertEqual(job.metrics["evaluation_method"], "leave_one_participant_out")
        self.assertEqual(job.metrics["train_participant_count"] + job.metrics["test_participant_count"], 4)
        entry = ModelRegistry.objects.get(training_job=job)
        card = build_model_card(entry)
        self.assertTrue(card["activation"]["allowed"], card["activation"]["blockers"])
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse("model-registry-activate", args=[entry.pk]), {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_queued_m1_job_exposes_schema_and_lopo_configuration(self):
        self.annotate_frontal_samples()
        self.client.force_authenticate(user=self.admin)
        with patch("apps.training.views._enqueue_training_job"), self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/training/jobs/create/", {
                "dataset_ids": [self.dataset.pk], "view_angle": "frontal",
                "prediction_target": "knee_alignment",
            }, format="json")
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(response.data["feature_schema_version"], "fppa_v2")
        self.assertEqual(response.data["split_strategy"], "leave_one_participant_out")
        self.assertNotIn("test_size", response.data)
        self.assertNotIn("random_seed", response.data)
        self.assertEqual(response.data["hyperparameters"], {
            "n_estimators": 100, "learning_rate": 0.1, "max_depth": 2,
        })

    def test_knee_alignment_loader_keeps_only_final_good_and_bad_targets(self):
        samples = list(
            self.dataset.samples.filter(
                dataset_video__view_angle=self.frontal_view_angle
            ).order_by("id")[:2]
        )
        for sample, grade in zip(samples, ("aligned", "deviated")):
            KneeAnnotation.objects.create(
                sample=sample,
                annotation={
                    "left": {"grade": grade, "direction": "uncertain"},
                    "right": {"grade": "aligned", "direction": "none"},
                    "notes": "",
                },
                annotator=self.admin,
            )

        sample_set = build_samples(
            [self.dataset],
            list(M1_FEATURES),
            view_angle="frontal",
            prediction_target="knee_alignment",
        )

        self.assertEqual(set(sample_set.labels), {"good", "bad"})
        self.assertTrue(all(row["label_origin"] == "human" for row in sample_set.sample_metadata))
        self.assertTrue(
            all(item["annotator_ids"] == [self.admin.pk] for item in sample_set.sample_metadata)
        )

        from apps.datasets.serializers import DatasetSerializer

        stats = DatasetSerializer(self.dataset).data["angle_training_stats"]["frontal"]
        self.assertEqual(stats["knee_target_sample_count"], 2)
        self.assertEqual(stats["knee_label_counts"]["good"], 1)
        self.assertEqual(stats["knee_label_counts"]["bad"], 1)
        self.assertEqual(stats["knee_label_counts"]["missing"], 6)

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

    def test_build_samples_uses_recorded_frame_timestamps(self):
        samples = build_samples(
            [self.dataset], list(FEATURE_ORDER), view_angle="diagonal"
        )
        self.assertTrue(
            all(item["timing_source"] == "frame_timestamps" for item in samples.sample_metadata)
        )

    def test_build_samples_excludes_samples_with_invalid_timestamps(self):
        sample = self.dataset.samples.filter(
            dataset_video__view_angle=self.view_angle
        ).first()
        sample.rep_assessment.landmark_series = [
            {
                "landmarks": frame["landmarks"],
                "frame_index": index,
                "timestamp_ms": 0.0,
                "native_fps": 30.0,
            }
            for index, frame in enumerate(make_landmark_series())
        ]
        sample.rep_assessment.save(update_fields=["landmark_series"])

        samples = build_samples([self.dataset], list(FEATURE_ORDER), view_angle="diagonal")
        self.assertNotIn(sample.pk, samples.sample_ids)
        self.assertTrue(any("timestamps" in error for error in samples.errors))

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
        with self.assertRaisesRegex(DatasetNotUsableError, "only one target class"):
            build_samples(
                [self.dataset],
                list(FEATURE_ORDER),
                view_angle="diagonal",
                prediction_target="error_type",
            )

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
            hyperparameters={"n_estimators": 10},
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
        self.assertEqual(train_sample_ids, test_sample_ids)
        from .config import TASK_PROFILES, default_hyperparameters
        manifest = job.training_manifest
        self.assertEqual(manifest["user_hyperparameters"], {
            **default_hyperparameters(), "n_estimators": 10,
        })
        self.assertEqual(manifest["locked_hyperparameters"], TASK_PROFILES["quality"])
        self.assertEqual(manifest["task_profile"], "quality")
        self.assertEqual(manifest["seed"], 42)
        self.assertEqual(manifest["xgboost_version"], manifest["environment"]["xgboost"])
        self.assertNotIn("test_size", manifest)
        for fold in manifest["folds"]:
            self.assertFalse(set(fold["train_sample_ids"]) & set(fold["test_sample_ids"]))
            self.assertEqual(fold["scale_pos_weight"], 1.0)
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
        registry = ModelRegistry.objects.get(training_job=job)
        activate_url = reverse("model-registry-activate", args=[registry.pk])
        activation = self.client.post(activate_url, {}, format="json")
        self.assertEqual(activation.status_code, 409, activation.data)
        registry.refresh_from_db()
        self.assertFalse(registry.is_active)

        state_url = reverse("model-state", args=[registry.pk])
        state = self.client.get(state_url)
        self.assertEqual(state.status_code, 200, state.data)
        self.assertEqual(state.data["view_angle"], "diagonal")
        self.assertEqual(state.data["prediction_target"], "binary_form")
        self.assertEqual(state.data["training"]["sample_count"], 8)
        self.assertTrue(state.data["artifact_available"])
        self.assertEqual(state.data["training_manifest"]["view_angle"], "diagonal")

        card = state.data["model_card"]
        self.assertEqual(card["schema_version"], "model_card_v1")
        self.assertEqual(card["status"], "blocked")
        self.assertFalse(card["activation"]["allowed"])
        self.assertIn(
            "feature_schema",
            {blocker["code"] for blocker in card["activation"]["blockers"]},
        )
        self.assertEqual(card["class_mapping"], {"0": "BAD_FORM", "1": "GOOD_FORM"})
        self.assertEqual(card["target_names"], ["BAD_FORM", "GOOD_FORM"])
        self.assertEqual(card["data_provenance"]["participant_count"], 4)

        evaluation = state.data["evaluation"]
        self.assertEqual(
            evaluation["class_mapping"], {"0": "BAD_FORM", "1": "GOOD_FORM"}
        )
        self.assertEqual(evaluation["target_names"], ["BAD_FORM", "GOOD_FORM"])
        self.assertEqual(len(evaluation["per_class"]), 2)
        self.assertEqual(evaluation["per_class"][0]["label"], "BAD_FORM")
        self.assertEqual(
            evaluation["test_count"], state.data["training"]["test_count"]
        )

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
        self.assertEqual(prediction.status_code, 404, prediction.data)

    def test_training_job_api_queues_after_commit(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            "dataset_ids": [self.dataset.pk],
            "view_angle": "diagonal",
            "prediction_target": "binary_form",
            "feature_selection": list(FEATURE_ORDER),
        }
        with patch("apps.training.tasks.run_training_job_task.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("training-job-create"), payload, format="json"
                )

        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(response.data["status"], TrainingJob.Status.PENDING)
        self.assertEqual(response.data["feature_schema_version"], FEATURE_SCHEMA_VERSION)
        delay.assert_called_once()
        self.assertEqual(delay.call_args.args[0], response.data["id"])

    def test_training_queue_failure_is_recorded(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            "dataset_ids": [self.dataset.pk],
            "view_angle": "diagonal",
            "prediction_target": "binary_form",
        }
        with patch(
            "apps.training.tasks.run_training_job_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("training-job-create"), payload, format="json"
                )

        self.assertEqual(response.status_code, 202, response.data)
        job = TrainingJob.objects.get(pk=response.data["id"])
        self.assertEqual(job.status, TrainingJob.Status.FAILED)
        self.assertIn("broker unavailable", job.error_message)

    @override_settings(MEDIA_ROOT=TEMP)
    def test_model_card_blocks_activation_when_manifest_hash_is_tampered(self):
        job = TrainingJob.objects.create()
        run_training_job(
            job,
            dataset_ids=[self.dataset.pk],
            hyperparameters={"n_estimators": 10},
            view_angle="diagonal",
        )
        job.refresh_from_db()
        registry = ModelRegistry.objects.get(training_job=job)

        manifest = dict(job.training_manifest)
        manifest["manifest_sha256"] = "0" * 64
        job.training_manifest = manifest
        job.save(update_fields=["training_manifest"])

        self.client.force_authenticate(user=self.admin)
        state = self.client.get(reverse("model-state", args=[registry.pk]))
        self.assertEqual(state.status_code, 200, state.data)

        card = state.data["model_card"]
        self.assertFalse(card["activation"]["allowed"])
        self.assertEqual(card["status"], "blocked")
        failed_codes = {blocker["code"] for blocker in card["activation"]["blockers"]}
        self.assertIn("manifest_integrity", failed_codes)

        activation = self.client.post(
            reverse("model-registry-activate", args=[registry.pk]),
            {},
            format="json",
        )
        self.assertEqual(activation.status_code, 409, activation.data)
        self.assertIn("manifest_integrity", {
            blocker["code"] for blocker in activation.data["blockers"]
        })
        registry.refresh_from_db()
        self.assertFalse(registry.is_active)

    def test_knee_alignment_evaluation_exposes_named_classes(self):
        from .serializers import ModelStateSerializer

        job = TrainingJob.objects.create(
            algorithm=TrainingJob.Algorithm.XGBOOST,
            view_angle="frontal",
            prediction_target=TrainingJob.PredictionTarget.KNEE_ALIGNMENT,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            status=TrainingJob.Status.COMPLETED,
            sample_count=12,
            train_count=6,
            test_count=6,
            metrics={
                "accuracy": 0.8333,
                "balanced_accuracy": 0.8,
                "precision": 0.8,
                "recall": 0.8,
                "f1": 0.8,
                "confusion_matrix": [[2, 1], [0, 3]],
                "class_mapping": {"0": "bad", "1": "good"},
                "target_names": ["bad", "good"],
                "test_class_distribution": {"bad": 3, "good": 3},
            },
            training_manifest={
                "class_mapping": {"0": "bad", "1": "good"},
                "target_names": ["bad", "good"],
                "test_sample_ids": [1, 2, 3, 4, 5, 6],
                "samples": [],
            },
        )
        registry = ModelRegistry.objects.create(
            name="knee-model",
            version="1.0",
            training_job=job,
            algorithm=TrainingJob.Algorithm.XGBOOST,
            artifact="model_registry/missing.json",
            metrics=job.metrics,
        )

        payload = ModelStateSerializer(registry).data
        evaluation = payload["evaluation"]
        self.assertEqual(evaluation["class_mapping"], {"0": "bad", "1": "good"})
        self.assertEqual(evaluation["target_names"], ["bad", "good"])
        self.assertEqual([item["label"] for item in evaluation["per_class"]], ["bad", "good"])
        bad_class = evaluation["per_class"][0]
        self.assertEqual(bad_class["support"], 3)
        self.assertAlmostEqual(bad_class["precision"], 1.0)
        self.assertAlmostEqual(bad_class["recall"], 2 / 3)
        self.assertEqual(payload["model_card"]["target_names"], ["bad", "good"])
        self.assertEqual(payload["model_card"]["prediction_target"], "knee_alignment")
