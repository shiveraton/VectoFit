"""analysis engine module to orchestrate the analysis of the four
deliverable features and construct the final assessment result"""

import numpy as np

from .bilateral_asymmetry import calculate_asymmetry_series
from .classifier import classify_metrics
from .joint_angle_analysis import calculate_angle_series
from .kinematic_velocity import calculate_velocity_series
from .range_of_motion import calculate_rom
from .result_builder import build_result
from .trunk_angle_analysis import calculate_trunk_angle_series


def analyze(landmark_series, thresholds):
    metrics = {}

    required_landmarks = {
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_ankle",
        "right_ankle",
    }

    missing_landmarks = required_landmarks - set(landmark_series[0])

    if missing_landmarks:
        raise ValueError(
            f"landmark_series frames are missing required landmarks: {sorted(missing_landmarks)}"
        )

    left_hip_angles = calculate_angle_series(
        landmark_series,
        "left_shoulder",
        "left_hip",
        "left_knee",
    )

    right_hip_angles = calculate_angle_series(
        landmark_series,
        "right_shoulder",
        "right_hip",
        "right_knee",
    )

    trunk_angles = calculate_trunk_angle_series(landmark_series)

    frame_interval = 1.0 / 30.0
    hip_midpoints = []
    for frame in landmark_series:
        left = np.asarray(frame["left_hip"], dtype=float)
        right = np.asarray(frame["right_hip"], dtype=float)
        hip_midpoints.append({"hip_midpoint": (left + right) / 2.0})
    velocity_series = calculate_velocity_series(
        hip_midpoints, "hip_midpoint", frame_interval
    )
    metrics["velocity"] = float(np.mean(velocity_series)) if velocity_series else 0.0

    left_knee_angles = calculate_angle_series(
        landmark_series,
        "left_hip",
        "left_knee",
        "left_ankle",
    )

    right_knee_angles = calculate_angle_series(
        landmark_series,
        "right_hip",
        "right_knee",
        "right_ankle",
    )

    metrics["hip_angle"] = min(min(left_hip_angles), min(right_hip_angles))
    metrics["trunk_angle"] = trunk_angles
    metrics["knee_angle"] = min(min(left_knee_angles), min(right_knee_angles))
    metrics["rom"] = calculate_rom(left_knee_angles)

    asymmetry_series = calculate_asymmetry_series(left_knee_angles, right_knee_angles)

    valid_asymmetry = [
        value for value in asymmetry_series if value is not None and np.isfinite(value)
    ]
    metrics["asymmetry"] = (
        float(np.median(valid_asymmetry)) if valid_asymmetry else None
    )

    valid_asymmetry_indices = [
        index
        for index, value in enumerate(asymmetry_series)
        if value is not None and np.isfinite(value)
    ]

    valid_knee_indices = [
        index
        for index, (left, right) in enumerate(zip(left_knee_angles, right_knee_angles))
        if np.isfinite(left) and np.isfinite(right)
    ]

    if valid_asymmetry_indices and valid_knee_indices:
        bottom_index = min(
            valid_knee_indices,
            key=lambda index: (
                left_knee_angles[index] + right_knee_angles[index],
                index,
            ),
        )

        asymmetry_index = min(
            valid_asymmetry_indices,
            key=lambda index: (
                left_knee_angles[index] + right_knee_angles[index],
                index,
            ),
        )

    classifications = classify_metrics(metrics, thresholds)

    result = build_result(metrics, classifications)

    return result
