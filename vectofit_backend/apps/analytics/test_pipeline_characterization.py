import unittest

from apps.analytics.services.features import (
    FEATURE_ORDER,
    FEATURE_SCHEMA_VERSION,
    extract_rep_features,
)
from apps.analytics.services.segmentation import segment_reps


class SegmentationCharacterizationTests(unittest.TestCase):
    def test_segmenter_returns_local_start_bottom_and_end_indices(self):
        hip_y = [110, 100, 95]
        hip_y.extend(95 + step * 5.5 for step in range(1, 11))
        hip_y.extend(150 - step * 5.5 for step in range(1, 11))
        hip_y.extend([100, 105])
        frames = [
            {"left_hip": {"y": value}, "right_hip": {"y": value}} for value in hip_y
        ]

        reps = segment_reps(frames)

        self.assertEqual(len(reps), 1)
        self.assertEqual(reps[0], {"start": 2, "bottom": 12, "end": 23})


class FppaAsymmetryFeatureTests(unittest.TestCase):
    def test_schema_and_feature_order_match_fppa_training_features(self):
        self.assertEqual(FEATURE_SCHEMA_VERSION, "fppa_v2")
        self.assertEqual(
            FEATURE_ORDER,
            [
                "fppa_l_bottom",
                "fppa_r_bottom",
                "fppa_l_peak",
                "fppa_r_peak",
                "asym_bottom",
                "asym_peak",
            ],
        )
        frames = [
            {
                "left_hip": [20.0, 10.0],
                "right_hip": [80.0, 10.0],
                "left_knee": [20.0, 40.0],
                "right_knee": [80.0, 40.0],
                "left_ankle": [20.0, 70.0],
                "right_ankle": [80.0, 70.0],
            }
            for _ in range(12)
        ]

        features = extract_rep_features(
            frames,
            frame_width=100,
            frame_height=100,
            native_fps=30.0,
            sample_step=1,
        )

        self.assertEqual(list(features), FEATURE_ORDER)
        self.assertTrue(all(abs(value) < 1e-9 for value in features.values()))
