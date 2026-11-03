import unittest

from apps.analytics.services import features as F
from apps.analytics.services import fppa
from apps.analytics.services.landmark_schema import LANDMARK_SCHEMA_VERSION

KW = {"frame_width": 100, "frame_height": 100, "native_fps": 30, "sample_step": 1}
NAN = float("nan")


def frame(l_shift=0.0, r_shift=0.0, left_on_right=True):
    lx, rx = (60.0, 40.0) if left_on_right else (40.0, 60.0)
    toward = -1.0 if left_on_right else 1.0
    return {
        "left_hip": [lx, 20.0],
        "left_knee": [lx + toward * l_shift, 50.0],
        "left_ankle": [lx, 80.0],
        "right_hip": [rx, 20.0],
        "right_knee": [rx - toward * r_shift, 50.0],
        "right_ankle": [rx, 80.0],
    }


def rep(n=9, **kw):
    return [frame(**kw) for _ in range(n)]


class ContractTests(unittest.TestCase):
    def test_single_schema_version_owned_by_fppa(self):
        self.assertEqual(F.FEATURE_SCHEMA_VERSION, "fppa_v2")
        self.assertIs(F.FEATURE_SCHEMA_VERSION, fppa.FEATURE_SCHEMA_VERSION)

    def test_model_version_selection(self):
        m0 = F.extract_rep_features(rep(l_shift=5, r_shift=5), model_version="M0", **KW)
        m1 = F.extract_rep_features(rep(l_shift=5, r_shift=5), model_version="M1", **KW)
        self.assertEqual(list(m0), F.M0_FEATURE_ORDER)
        self.assertEqual(list(m1), F.FEATURE_ORDER)

    def test_requested_none_means_model_default_not_everything(self):
        self.assertEqual(F.validate_features(None, "M0"), F.M0_FEATURE_ORDER)
        with self.assertRaises(F.FeatureExtractionError):
            F.validate_features(["asym_bottom"], "M0")
        with self.assertRaises(F.FeatureExtractionError):
            F.validate_features(None, "M9")


class GeometryRegressionTests(unittest.TestCase):
    def test_valid_frames_are_not_rejected(self):
        out = F.extract_rep_features(rep(), **KW)
        self.assertTrue(all(abs(v) < 1e-9 for v in out.values()))

    def test_knee_in_positive_knee_out_negative(self):
        valgus = F.extract_rep_features(rep(l_shift=5, r_shift=5), **KW)
        varus = F.extract_rep_features(rep(l_shift=-5, r_shift=-5), **KW)
        for k in ("fppa_l_bottom", "fppa_r_bottom", "fppa_l_peak", "fppa_r_peak"):
            self.assertGreater(valgus[k], 0)
            self.assertLess(varus[k], 0)

    def test_sign_independent_of_screen_side(self):
        a = F.extract_rep_features(rep(l_shift=5, r_shift=5, left_on_right=True), **KW)
        b = F.extract_rep_features(rep(l_shift=5, r_shift=5, left_on_right=False), **KW)
        for k in a:
            self.assertAlmostEqual(a[k], b[k])

    def test_feature_names_follow_anatomical_side(self):
        out = F.extract_rep_features(rep(l_shift=5, r_shift=0), **KW)
        self.assertGreater(out["fppa_l_bottom"], 0)
        self.assertAlmostEqual(out["fppa_r_bottom"], 0.0)
        self.assertAlmostEqual(out["asym_bottom"], abs(out["fppa_l_bottom"]))
        swapped = F.extract_rep_features(rep(l_shift=0, r_shift=5), **KW)
        self.assertAlmostEqual(swapped["fppa_l_bottom"], 0.0)
        self.assertGreater(swapped["fppa_r_bottom"], 0)

    def test_identical_sides_zero_asymmetry(self):
        out = F.extract_rep_features(rep(l_shift=4, r_shift=4), **KW)
        self.assertAlmostEqual(out["asym_bottom"], 0.0)
        self.assertAlmostEqual(out["asym_peak"], 0.0)


class InvalidInputTests(unittest.TestCase):
    def test_zero_placeholder_landmark_rejected(self):
        frames = rep()
        for f in frames:
            f["left_knee"] = [0.0, 0.0]
        with self.assertRaises(F.FeatureExtractionError):
            F.extract_rep_features(frames, **KW)

    def test_nan_everywhere_raises_feature_error_not_valueerror(self):
        frames = rep()
        for f in frames:
            f["left_knee"] = [NAN, 50.0]
        with self.assertRaises(F.FeatureExtractionError):
            F.extract_rep_features(frames, **KW)

    def test_isolated_invalid_frame_is_excluded_not_zero_filled(self):
        frames = rep(l_shift=5, r_shift=5)
        frames[4]["left_knee"] = [NAN, 50.0]
        out = F.extract_rep_features(frames, **KW)
        self.assertGreater(out["fppa_l_peak"], 15.0)
        self.assertGreater(out["fppa_l_bottom"], 15.0)

    def test_too_many_invalid_frames_rejected(self):
        frames = rep(l_shift=5, r_shift=5)
        for i in range(3):
            frames[i + 3]["right_knee"] = [NAN, 50.0]
        with self.assertRaises(F.FeatureExtractionError):
            F.extract_rep_features(frames, **KW)

    def test_rep_shorter_than_filter_window_rejected(self):
        with self.assertRaises(F.FeatureExtractionError):
            F.extract_rep_features(rep(n=5), **KW)

    def test_missing_landmark_rejected(self):
        frames = rep()
        for f in frames:
            del f["right_ankle"]
        with self.assertRaises(F.FeatureExtractionError):
            F.extract_rep_features(frames, **KW)


def stored_rep(
    l_shift=0.0, r_shift=0.0, n=12, step_ms=1000.0 / 30.0, width=100, height=100
):
    frames = []
    for index in range(n):
        landmarks = {
            name: {
                "x": x / width,
                "y": y / height,
                "z": 0.0,
                "visibility": 0.99,
                "normalized": True,
            }
            for name, (x, y) in frame(l_shift, r_shift).items()
        }
        frames.append(
            {
                "frame_index": index,
                "timestamp_ms": index * step_ms,
                "landmarks": landmarks,
            }
        )
    return {"schema_version": LANDMARK_SCHEMA_VERSION, "frames": frames}


class EffectiveFpsTests(unittest.TestCase):
    def test_recovers_sampling_rate_from_timestamps(self):
        self.assertEqual(fppa.effective_fps(stored_rep()["frames"]), 30.0)
        self.assertEqual(
            fppa.effective_fps(stored_rep(step_ms=1000 / 15)["frames"]), 15.0
        )
        self.assertEqual(
            fppa.effective_fps(stored_rep(step_ms=1000 / 29.97)["frames"]), 29.97
        )

    def test_none_when_timing_is_unusable(self):
        frames = stored_rep()["frames"]
        self.assertIsNone(fppa.effective_fps([]))
        self.assertIsNone(fppa.effective_fps(frames[:1]))
        self.assertIsNone(
            fppa.effective_fps([{**f, "timestamp_ms": None} for f in frames])
        )
        self.assertIsNone(
            fppa.effective_fps([{**f, "timestamp_ms": NAN} for f in frames])
        )
        self.assertIsNone(
            fppa.effective_fps([{**f, "timestamp_ms": 5.0} for f in frames])
        )


class StoredRepEntryPointTests(unittest.TestCase):
    def test_compute_rep_fppa_matches_explicit_timing_call(self):
        rep = stored_rep(5, 2)
        direct, status = F.compute_rep_fppa(rep, frame_width=100, frame_height=100)
        explicit, explicit_status = fppa.extract_fppa_features(
            rep["frames"],
            frame_width=100,
            frame_height=100,
            native_fps=30.0,
            sample_step=1,
        )
        self.assertEqual(direct, explicit)
        self.assertEqual(status, explicit_status)

    def test_structural_problems_return_a_reason_and_never_raise(self):
        rep = stored_rep()
        cases = [
            (None, "missing_landmark_data"),
            ([], "missing_landmark_data"),
            ({}, "unsupported_landmark_schema"),
            (
                {"schema_version": "landmarks_v1", "frames": rep["frames"]},
                "unsupported_landmark_schema",
            ),
            (
                {"schema_version": LANDMARK_SCHEMA_VERSION, "frames": []},
                "missing_landmark_frames",
            ),
        ]
        for data, reason in cases:
            features, status = F.compute_rep_fppa(
                data, frame_width=100, frame_height=100
            )
            self.assertIsNone(features)
            self.assertEqual(status, {"valid": False, "reason": reason})
        self.assertEqual(
            F.compute_rep_fppa(rep, frame_width=None, frame_height=100)[1]["reason"],
            "missing_frame_size",
        )
        no_timing = {
            **rep,
            "frames": [{**f, "timestamp_ms": None} for f in rep["frames"]],
        }
        self.assertEqual(
            F.compute_rep_fppa(no_timing, frame_width=100, frame_height=100)[1][
                "reason"
            ],
            "missing_frame_timing",
        )

    def test_extract_features_for_rep_selects_and_orders(self):
        rep = stored_rep(5, 5)
        m0 = F.extract_features_for_rep(
            rep, frame_width=100, frame_height=100, model_version="M0"
        )
        m1 = F.extract_features_for_rep(rep, frame_width=100, frame_height=100)
        self.assertEqual(list(m0), F.M0_FEATURE_ORDER)
        self.assertEqual(list(m1), F.M1_FEATURE_ORDER)
        subset = F.extract_features_for_rep(
            rep,
            frame_width=100,
            frame_height=100,
            requested=["asym_peak", "fppa_l_bottom"],
        )
        self.assertEqual(
            list(subset), ["fppa_l_bottom", "asym_peak"]
        )  # canonical order

    def test_extract_features_for_rep_raises_with_the_reason(self):
        with self.assertRaisesRegex(
            F.FeatureExtractionError, "unsupported_landmark_schema"
        ):
            F.extract_features_for_rep({}, frame_width=100, frame_height=100)
        with self.assertRaisesRegex(
            F.FeatureExtractionError, "shorter_than_filter_window"
        ):
            F.extract_features_for_rep(
                stored_rep(n=4), frame_width=100, frame_height=100
            )

    def test_model_version_for_selection(self):
        self.assertEqual(F.model_version_for(F.M0_FEATURE_ORDER), "M0")
        self.assertEqual(F.model_version_for(F.M1_FEATURE_ORDER), "M1")
        self.assertEqual(F.model_version_for(["fppa_l_peak", "asym_peak"]), "M1")

    def test_to_feature_row_rejects_missing_and_non_finite(self):
        self.assertEqual(F.to_feature_row({"a": 1, "b": 2.5}, ["b", "a"]), [2.5, 1.0])
        with self.assertRaises(F.FeatureExtractionError):
            F.to_feature_row({"a": 1}, ["a", "b"])
        with self.assertRaises(F.FeatureExtractionError):
            F.to_feature_row({"a": NAN}, ["a"])


if __name__ == "__main__":
    unittest.main()
