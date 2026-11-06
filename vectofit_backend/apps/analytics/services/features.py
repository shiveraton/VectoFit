import numpy as np

from .bilateral_asymmetry import calculate_asymmetry_series
from .joint_angle_analysis import calculate_angle_series
from .kinematic_velocity import calculate_velocity_series
from .range_of_motion import calculate_rom
from .trunk_angle_analysis import calculate_trunk_angle_series

FEATURE_SCHEMA_VERSION = "python_rep_features_v2"


AVAILABLE_FEATURES = [
    "hip_angle",
    "knee_angle",
    "rom",
    "asymmetry",
    "trunk_angle",
    "velocity",
]

FEATURE_ORDER = [
    "hip_angle",
    "knee_angle",
    "rom",
    "asymmetry",
    "trunk_angle_mean",
    "trunk_angle_max",
    "trunk_angle_range",
    "velocity_mean",
    "velocity_peak",
]

REQUIRED_LANDMARKS = [
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


class FeatureExtractionError(Exception):
    """Raised when a repetition's landmarks cannot yield usable features."""


def validate_features(requested):
    if requested is None:
        return list(FEATURE_ORDER)

    if not isinstance(requested, (list, tuple)):
        raise FeatureExtractionError("feature_selection must be a list of names.")

    unknown = [f for f in requested if f not in AVAILABLE_FEATURES]
    if unknown:
        raise FeatureExtractionError(
            f"Unknown feature(s) {unknown}. Available: {AVAILABLE_FEATURES}"
        )

    selected = []
    for name in requested:
        if name == "trunk_angle":
            selected.extend(
                ["trunk_angle_mean", "trunk_angle_max", "trunk_angle_range"]
            )
        elif name == "velocity":
            selected.extend(["velocity_mean", "velocity_peak"])
        else:
            selected.append(name)

    return [f for f in FEATURE_ORDER if f in set(selected)]


def _validate_series(landmark_series):
    if not landmark_series:
        raise FeatureExtractionError("Repetition has no landmark frames.")

    for index, frame in enumerate(landmark_series):
        missing = [name for name in REQUIRED_LANDMARKS if name not in frame]
        if missing:
            raise FeatureExtractionError(
                f"Frame {index} is missing landmarks: {missing}"
            )

        for name in REQUIRED_LANDMARKS:
            point = np.asarray(frame[name], dtype=float)
            if point.shape != (2,) or not np.all(np.isfinite(point)):
                raise FeatureExtractionError(
                    f"Frame {index} landmark {name!r} is not a finite [x, y] pair."
                )
            if not np.any(point):
                raise FeatureExtractionError(
                    f"Frame {index} landmark {name!r} is degenerate (all zeros)."
                )


def extract_rep_features(landmark_series, fps=None, scale_factor=None):
    _validate_series(landmark_series)

    if fps is None or fps <= 0:
        raise FeatureExtractionError(
            "A positive fps is required to compute velocity (KVT)."
        )

    left_knee_angles = calculate_angle_series(
        landmark_series, "left_hip", "left_knee", "left_ankle"
    )
    right_knee_angles = calculate_angle_series(
        landmark_series, "right_hip", "right_knee", "right_ankle"
    )
    left_hip_angles = calculate_angle_series(
        landmark_series, "left_shoulder", "left_hip", "left_knee"
    )
    right_hip_angles = calculate_angle_series(
        landmark_series, "right_shoulder", "right_hip", "right_knee"
    )

    rom_degrees = calculate_rom(left_knee_angles)

    asymmetry_values = calculate_asymmetry_series(left_knee_angles, right_knee_angles)
    asymmetry_values = [a for a in asymmetry_values if a is not None]
    max_asymmetry = max(asymmetry_values) if asymmetry_values else 0.0

    trunk_angles = np.asarray(
        calculate_trunk_angle_series(landmark_series), dtype=float
    )

    hip_midpoints = []
    for frame in landmark_series:
        left = np.asarray(frame["left_hip"], dtype=float)
        right = np.asarray(frame["right_hip"], dtype=float)
        hip_midpoints.append({"hip_midpoint": (left + right) / 2.0})

    frame_interval = 1.0 / float(fps)
    velocity_series = calculate_velocity_series(
        hip_midpoints, "hip_midpoint", frame_interval
    )

    if not velocity_series:
        raise FeatureExtractionError(
            "Repetition is too short to compute a velocity (KVT) series."
        )

    features = {
        "hip_angle": float(min(min(left_hip_angles), min(right_hip_angles))),
        "knee_angle": float(min(min(left_knee_angles), min(right_knee_angles))),
        "rom": float(rom_degrees),
        "asymmetry": float(max_asymmetry),
        "trunk_angle_mean": float(np.mean(trunk_angles)),
        "trunk_angle_max": float(np.max(trunk_angles)),
        "trunk_angle_range": float(np.max(trunk_angles) - np.min(trunk_angles)),
        "velocity_mean": float(np.mean(velocity_series)),
        "velocity_peak": float(np.max(velocity_series)),
    }

    warnings = []
    if scale_factor:
        for key in ("velocity_mean", "velocity_peak"):
            features[key] = features[key] / float(scale_factor)
    else:
        warnings.append(
            "No scale_factor supplied: velocity remains in pixel units. "
            "Velocity comparisons across subjects are not normalized."
        )

    if not warnings:
        pass

    features["_warnings"] = warnings
    return features


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
