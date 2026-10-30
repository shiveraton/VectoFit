"""Baseline contracts for the pre-refactor FPPA input pipeline."""

import unittest

from apps.analytics.services.features import (
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
            {"left_hip": {"y": value}, "right_hip": {"y": value}}
            for value in hip_y
        ]

        reps = segment_reps(frames)

        self.assertEqual(len(reps), 1)
        self.assertEqual(reps[0], {"start": 2, "bottom": 12, "end": 23})


class PythonRepFeaturesV1CharacterizationTests(unittest.TestCase):
    def test_schema_and_feature_values_remain_pinned(self):
        self.assertEqual(FEATURE_SCHEMA_VERSION, "python_rep_features_v1")
        frames = []
        for offset in (0.0, 1.0):
            frames.append(
                {
                    "left_shoulder": [40.0, 10.0 + offset],
                    "right_shoulder": [60.0, 10.0 + offset],
                    "left_hip": [42.0, 40.0 + offset],
                    "right_hip": [58.0, 40.0 + offset],
                    "left_knee": [43.0, 65.0 + offset],
                    "right_knee": [57.0, 65.0 + offset],
                    "left_ankle": [44.0, 90.0 + offset],
                    "right_ankle": [56.0, 90.0 + offset],
                }
            )

        features = extract_rep_features(frames, fps=30.0, scale_factor=2.0)

        self.assertAlmostEqual(features["hip_angle"], 178.4765352083483)
        self.assertAlmostEqual(features["knee_angle"], 180.0)
        self.assertAlmostEqual(features["rom"], 0.0)
        self.assertAlmostEqual(features["asymmetry"], 0.0)
        self.assertAlmostEqual(features["velocity_mean"], 15.0)
        self.assertAlmostEqual(features["velocity_peak"], 15.0)
        self.assertEqual(features["_warnings"], [])

