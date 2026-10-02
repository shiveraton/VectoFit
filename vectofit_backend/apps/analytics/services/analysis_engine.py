"""analysis engine module to orchestrate the analysis of the four
deliverable features and construct the final assessment result"""

from .joint_angle_analysis import calculate_angle_series
from .range_of_motion import calculate_rom
from .bilateral_asymmetry import calculate_asymmetry_series
from .kinematic_velocity import calculate_velocity_series
from .trunk_angle_analysis import calculate_trunk_angle_series
from .classifier import classify_metrics
from .result_builder import build_result

import numpy as np

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

    # KVT: velocity of the hip midpoint (trunk centre of mass) over the rep.
    # A frame interval is required; callers that know the source fps should
    # pass it. 30 fps matches the VideoProcessor's downsampling target.
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
    metrics["asymmetry"] = max(calculate_asymmetry_series(left_knee_angles, right_knee_angles))

    classifications = classify_metrics(
        metrics,
        thresholds
    )

    result = build_result(
        metrics,
        classifications
    )

    return result