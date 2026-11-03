import unittest

from apps.analytics.services.fppa import extract_fppa_features, odd_filter_window


def _frame(knee_shift=0.0):
    return {
        "left_hip": {"x": 40.0, "y": 20.0, "visibility": 1.0},
        "right_hip": {"x": 60.0, "y": 20.0, "visibility": 1.0},
        "left_knee": {"x": 40.0 + knee_shift, "y": 50.0, "visibility": 1.0},
        "right_knee": {"x": 60.0 - knee_shift, "y": 50.0, "visibility": 1.0},
        "left_ankle": {"x": 40.0, "y": 80.0, "visibility": 1.0},
        "right_ankle": {"x": 60.0, "y": 80.0, "visibility": 1.0},
    }


class FppaV2Tests(unittest.TestCase):
    def _features(self, frames):
        return extract_fppa_features(
            frames,
            frame_width=100,
            frame_height=100,
            native_fps=30,
            sample_step=1,
        )

    def test_straight_leg_is_zero(self):
        features, validity = self._features([_frame() for _ in range(9)])
        self.assertTrue(validity["valid"])
        self.assertAlmostEqual(features["fppa_l_bottom"], 0.0)
        self.assertAlmostEqual(features["fppa_r_bottom"], 0.0)

    def test_knee_in_is_positive_for_both_legs(self):
        features, _ = self._features([_frame(5.0) for _ in range(9)])
        self.assertGreater(features["fppa_l_bottom"], 0.0)
        self.assertGreater(features["fppa_r_bottom"], 0.0)

    def test_horizontal_mirror_preserves_signed_values(self):
        original = [_frame(5.0) for _ in range(9)]
        mirrored = []
        for frame in original:
            mirrored.append(
                {
                    name: {**point, "x": 100.0 - point["x"]}
                    for name, point in frame.items()
                }
            )
        values, _ = self._features(original)
        mirrored_values, _ = self._features(mirrored)
        self.assertAlmostEqual(
            values["fppa_l_bottom"], mirrored_values["fppa_l_bottom"]
        )
        self.assertAlmostEqual(
            values["fppa_r_bottom"], mirrored_values["fppa_r_bottom"]
        )

    def test_window_is_odd_nearest_integer(self):
        self.assertEqual(odd_filter_window(30, 0.27), 9)
