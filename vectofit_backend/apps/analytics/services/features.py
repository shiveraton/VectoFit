import numpy as np

from .fppa import (  # noqa: F401
    FEATURE_SCHEMA_VERSION,
    effective_fps,
    extract_fppa_features,
)
from .landmark_schema import LANDMARK_SCHEMA_VERSION

M0_FEATURE_ORDER = [
    "fppa_l_bottom",
    "fppa_r_bottom",
    "fppa_l_peak",
    "fppa_r_peak",
]
M1_FEATURE_ORDER = [*M0_FEATURE_ORDER, "asym_bottom", "asym_peak"]

FEATURE_ORDERS = {"M0": M0_FEATURE_ORDER, "M1": M1_FEATURE_ORDER}
M0_FEATURES = M0_FEATURE_ORDER
M1_FEATURES = M1_FEATURE_ORDER
FEATURE_ORDER = M1_FEATURE_ORDER
ASYMMETRY_FEATURES = ("asym_bottom", "asym_peak")

FPPA_REQUIRED_LANDMARKS = [
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]
REQUIRED_LANDMARKS = ["left_shoulder", "right_shoulder", *FPPA_REQUIRED_LANDMARKS]


class FeatureExtractionError(Exception):
    """Raised when a repetition's landmarks cannot yield usable features."""


def validate_features(requested=None, model_version="M1"):
    if model_version not in FEATURE_ORDERS:
        raise FeatureExtractionError(
            f"Unknown model version: {model_version}. Available: {list(FEATURE_ORDERS)}"
        )
    available = FEATURE_ORDERS[model_version]
    if requested is None:
        return list(available)
    if not isinstance(requested, (list, tuple)):
        raise FeatureExtractionError("feature_selection must be a list of names.")
    unknown = [name for name in requested if name not in available]
    if unknown:
        raise FeatureExtractionError(
            f"Unknown feature(s) for {model_version}: {unknown}. Available: {available}"
        )
    selected = set(requested)
    return [name for name in available if name in selected]


def model_version_for(selected_features):
    return "M1" if set(selected_features) & set(ASYMMETRY_FEATURES) else "M0"


def extract_rep_features(
    landmark_series,
    requested=None,
    model_version="M1",
    *,
    frame_width,
    frame_height,
    native_fps,
    sample_step=1,
):
    selected = validate_features(requested=requested, model_version=model_version)
    fppa, status = extract_fppa_features(
        landmark_series,
        frame_width=frame_width,
        frame_height=frame_height,
        native_fps=native_fps,
        sample_step=sample_step,
    )
    if fppa is None:
        raise FeatureExtractionError(status.get("reason", "fppa_invalid"))
    return {name: float(fppa[name]) for name in selected}


def compute_rep_fppa(landmark_data, *, frame_width, frame_height):
    def invalid(reason):
        return None, {"valid": False, "reason": reason}

    if not isinstance(landmark_data, dict):
        return invalid("missing_landmark_data")
    if landmark_data.get("schema_version") != LANDMARK_SCHEMA_VERSION:
        return invalid("unsupported_landmark_schema")
    frames = landmark_data.get("frames")
    if not frames:
        return invalid("missing_landmark_frames")
    if not frame_width or not frame_height:
        return invalid("missing_frame_size")
    fps = effective_fps(frames)
    if fps is None:
        return invalid("missing_frame_timing")
    return extract_fppa_features(
        frames,
        frame_width=frame_width,
        frame_height=frame_height,
        native_fps=fps,
        sample_step=1,
    )


def extract_features_for_rep(
    landmark_data,
    *,
    frame_width,
    frame_height,
    requested=None,
    model_version="M1",
):
    selected = validate_features(requested=requested, model_version=model_version)
    fppa, status = compute_rep_fppa(
        landmark_data, frame_width=frame_width, frame_height=frame_height
    )
    if fppa is None:
        raise FeatureExtractionError(status.get("reason", "fppa_invalid"))
    return {name: float(fppa[name]) for name in selected}


def to_feature_row(features, selected_features):
    row = []
    for name in selected_features:
        if name not in features:
            raise FeatureExtractionError(
                f"Requested feature {name!r} is absent from the extracted sample."
            )
        value = float(features[name])
        if not np.isfinite(value):
            raise FeatureExtractionError(
                f"Feature {name!r} is not finite ({value}); refusing to build a row."
            )
        row.append(value)
    return row
