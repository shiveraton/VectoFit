import json
import unittest
from types import SimpleNamespace
from unittest import mock

from apps.analytics.services import features, fppa
from apps.assessments import views as assessment_views

from .services import data_loader

WIDTH, HEIGHT = 640, 360
DATASET = SimpleNamespace(pk=1, name="parity")


def make_entries(knee_in, n_frames=12, step_ms=1000.0 / 30.0, left_on_right=True):
    def point(x, y):
        return {
            "x": x * WIDTH,
            "y": y * HEIGHT,
            "z": 0.0,
            "x_normalized": x,
            "y_normalized": y,
            "visibility": 0.99,
        }

    left_x, right_x = (0.6, 0.4) if left_on_right else (0.4, 0.6)
    toward = -1.0 if left_on_right else 1.0
    entries = []
    for index in range(n_frames):
        hip_y = 0.40 + 0.01 * min(index, n_frames - index)
        entries.append(
            {
                "frame_index": index,
                "timestamp_ms": index * step_ms,
                "landmarks": {
                    "left_shoulder": point(left_x, 0.15),
                    "right_shoulder": point(right_x, 0.15),
                    "left_hip": point(left_x, hip_y),
                    "right_hip": point(right_x, hip_y),
                    "left_knee": point(left_x + toward * knee_in, 0.6),
                    "right_knee": point(right_x - toward * knee_in * 0.5, 0.6),
                    "left_ankle": point(left_x, 0.85),
                    "right_ankle": point(right_x, 0.85),
                },
            }
        )
    return entries


def run_inference_path(entries):
    captured = {}

    def fake_predict(**kwargs):
        captured.update(kwargs)
        return {"status": "ok"}

    session = SimpleNamespace(body_profile=None, view_angle="frontal")
    repetition_entries = [
        {
            "entries": entries,
            "key_frame_index": entries[len(entries) // 2]["frame_index"],
        }
    ]
    with (
        mock.patch.object(assessment_views, "analyze", return_value={}),
        mock.patch.object(
            assessment_views, "reference_template_from_profile", return_value=None
        ),
        mock.patch.object(
            assessment_views, "predict_with_active_model", side_effect=fake_predict
        ),
    ):
        prepared = assessment_views._prepare_assessments(
            session,
            repetition_entries,
            {},
            frame_width=WIDTH,
            frame_height=HEIGHT,
            native_fps=30.0,
            sample_step=1,
            config_hash="hash-1",
        )
    return captured, prepared[0]


def run_training_path(stored_reps, selected=None, model_version=None):
    samples = []
    for number, (rep, label) in enumerate(stored_reps, start=1):
        stored = SimpleNamespace(
            pk=number,
            landmark_data=json.loads(json.dumps(rep["landmark_data"])),
            pipeline_config_hash=rep["pipeline_config_hash"],
        )
        session = SimpleNamespace(
            processed_frame_width=WIDTH, processed_frame_height=HEIGHT
        )
        sample = SimpleNamespace(
            pk=number,
            is_correct=label,
            error_label="",
            label_source="human",
            annotator_id=1,
            annotated_at=None,
            dataset_video_id=None,
            dataset_video=None,
            participant=number,
        )
        samples.append((sample, stored, session))
    with mock.patch.multiple(
        data_loader,
        _resolve_view_angle=mock.Mock(return_value="frontal"),
        _validate_training_datasets=mock.Mock(return_value=None),
        _participant_id_for_sample=mock.Mock(side_effect=lambda s, d: s.participant),
        _load_labelled_samples=mock.Mock(return_value=iter(samples)),
    ):
        return data_loader.build_samples(
            [DATASET], selected, view_angle="frontal", model_version=model_version
        )


class TrainingInferenceParityTests(unittest.TestCase):
    def setUp(self):
        self.neutral = make_entries(0.0)
        self.valgus = make_entries(0.05)

    def test_view_and_loader_produce_identical_feature_vectors(self):
        inference_a, rep_a = run_inference_path(self.neutral)
        inference_b, rep_b = run_inference_path(self.valgus)
        sample_set = run_training_path([(rep_a, True), (rep_b, False)])

        self.assertEqual(sample_set.feature_names, features.FEATURE_ORDER)
        for row, seen in zip(sample_set.rows, (inference_a, inference_b)):
            expected = [seen["features"][name] for name in features.FEATURE_ORDER]
            self.assertEqual(row, expected)
        self.assertNotEqual(sample_set.rows[0], sample_set.rows[1])

    def test_inference_sends_the_current_schema_version_and_all_six_features(self):
        seen, rep = run_inference_path(self.valgus)
        self.assertEqual(seen["feature_schema_version"], fppa.FEATURE_SCHEMA_VERSION)
        self.assertEqual(list(seen["features"]), features.FEATURE_ORDER)
        self.assertEqual(rep["feature_schema_version"], fppa.FEATURE_SCHEMA_VERSION)
        stored = rep["analysis_result"]["fppa_v2"]
        self.assertTrue(stored["validity"]["valid"])
        self.assertEqual(stored["features"], seen["features"])

    def test_report_entry_and_model_input_come_from_one_extraction(self):
        seen, rep = run_inference_path(self.valgus)
        direct, _ = features.compute_rep_fppa(
            rep["landmark_data"], frame_width=WIDTH, frame_height=HEIGHT
        )
        self.assertEqual(seen["features"], direct)

    def test_m0_training_rows_are_a_prefix_of_the_m1_rows(self):
        _, rep_a = run_inference_path(self.neutral)
        _, rep_b = run_inference_path(self.valgus)
        reps = [(rep_a, True), (rep_b, False)]
        m0 = run_training_path(reps, model_version="M0")
        m1 = run_training_path(reps, model_version="M1")
        self.assertEqual(m0.feature_names, features.M0_FEATURE_ORDER)
        for row0, row1 in zip(m0.rows, m1.rows):
            self.assertEqual(row0, row1[: len(row0)])

    def test_loader_uses_timestamps_not_an_assumed_frame_rate(self):
        slow = make_entries(0.05, n_frames=12, step_ms=1000.0 / 15.0)
        seen, rep = run_inference_path(slow)
        status = rep["analysis_result"]["fppa_v2"]["validity"]
        self.assertEqual(status["filter_window"], fppa.odd_filter_window(15.0))
        sample_set = run_training_path(
            [
                (rep, True),
                (
                    run_inference_path(make_entries(0.0, step_ms=1000.0 / 15.0))[1],
                    False,
                ),
            ]
        )
        self.assertEqual(
            sample_set.rows[0], [seen["features"][n] for n in features.FEATURE_ORDER]
        )

    def test_per_side_features_keep_anatomical_meaning_regardless_of_screen_side(self):
        for left_on_right in (True, False):
            _, rep = run_inference_path(make_entries(0.05, left_on_right=left_on_right))
            stored = rep["analysis_result"]["fppa_v2"]["features"]
            self.assertGreater(stored["fppa_l_bottom"], stored["fppa_r_bottom"])
            self.assertGreater(stored["fppa_r_bottom"], 0)

    def test_invalid_rep_is_not_assessed_by_the_view_and_excluded_by_the_loader(self):
        broken = make_entries(0.05, n_frames=4)
        seen, rep = run_inference_path(broken)
        self.assertEqual(seen, {})
        prediction = rep["analysis_result"]["model_prediction"]
        self.assertEqual(prediction["status"], "not_assessed")
        self.assertEqual(prediction["reason"], "feature_extraction_failed")
        self.assertEqual(prediction["detail"], "shorter_than_filter_window")

        _, good_a = run_inference_path(self.neutral)
        _, good_b = run_inference_path(self.valgus)
        sample_set = run_training_path([(good_a, True), (good_b, False), (rep, True)])
        self.assertEqual(len(sample_set), 2)
        self.assertEqual(sample_set.exclusion_counts, {"shorter_than_filter_window": 1})


if __name__ == "__main__":
    unittest.main()
