from math import acos, degrees, hypot

import numpy as np
from scipy.signal import savgol_filter

FEATURE_SCHEMA_VERSION = "fppa_v2"
SIDES = ("left", "right")
M0_FEATURES = (
    "fppa_l_bottom",
    "fppa_r_bottom",
    "fppa_l_peak",
    "fppa_r_peak",
)
M1_FEATURES = M0_FEATURES + ("asym_bottom", "asym_peak")


def odd_filter_window(effective_fps: float, seconds: float = 0.27) -> int:
    target = max(1.0, float(effective_fps) * seconds)
    lower = max(1, int(target))
    if lower % 2 == 0:
        lower -= 1
    upper = lower + 2
    return min(
        (lower, upper), key=lambda candidate: (abs(candidate - target), candidate)
    )


def effective_fps(frames):
    times = []
    for frame in frames or []:
        value = frame.get("timestamps_ms") if isinstance(frame, dict) else None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(value):
            return None
        times.append(value)
    if len(times) < 2:
        return None
    step_ms = float(np.median(np.diff(times)))
    if not np.isfinite(step_ms) or step_ms <= 0:
        return None
    return round(1000.0 / step_ms, 2)


def _point(frame, landmark, width, height):
    landmarks = frame.get("landmarks", frame)
    item = landmarks.get(landmark)
    if item is None:
        return None
    if isinstance(item, dict):
        x, y = float(item["x"]), float(item["y"])
        visibility = float(item.get("visibility", 0.0))
        normalized = item.get("normalized", False)
    else:
        x, y = map(float, item[:2])
        visibility, normalized = 1.0, False
    if not (np.isfinite(x) and np.isfinite(y) and np.isfinite(visibility)):
        return None
    if x == 0.0 and y == 0.0:
        return None
    if normalized:
        x, y = x * width, y * height
    return np.array([x, y], dtype=float), visibility


def _signed_fppa(frame, side, width, height):
    hip = _point(frame, f"{side}_hip", width, height)
    knee = _point(frame, f"{side}_knee", width, height)
    ankle = _point(frame, f"{side}_ankle", width, height)
    if not all((hip, knee, ankle)) or min(hip[1], knee[1], ankle[1]) < 0.5:
        return None
    hip, knee, ankle = hip[0], knee[0], ankle[0]
    thigh, shank = knee - hip, ankle - knee
    denominator = hypot(*thigh) * hypot(*shank)
    if denominator == 0:
        return None
    theta = degrees(acos(float(np.clip(np.dot(thigh, shank) / denominator, -1, 1))))
    left_hip = _point(frame, "left_hip", width, height)
    right_hip = _point(frame, "right_hip", width, height)
    if left_hip is None or right_hip is None:
        return None
    hip_mid_x = (left_hip[0][0] + right_hip[0][0]) / 2
    line_x = (
        hip[0] + (ankle[0] - hip[0]) * ((knee[1] - hip[1]) / (ankle[1] - hip[1]))
        if ankle[1] != hip[1]
        else hip[0]
    )
    sign = 1.0 if (knee[0] - line_x) * np.sign(hip_mid_x - hip[0]) > 0 else -1.0
    return float(sign * theta)


def _smooth_valid_runs(values, window):
    output = [None] * len(values)
    i = 0
    while i < len(values):
        if values[i] is None:
            i += 1
            continue
        j = i
        while j < len(values) and values[j] is not None:
            j += 1
        run = np.asarray(values[i:j], dtype=float)
        median = np.asarray(
            [
                np.median(run[max(0, k - 1) : min(len(run), k + 2)])
                for k in range(len(run))
            ]
        )
        if len(run) >= window:
            median = savgol_filter(median, window, 2, mode="interp")
        output[i:j] = median.tolist()
        i = j
    return output


def extract_fppa_features(
    landmark_series, *, frame_width, frame_height, native_fps, sample_step=1
):
    frames = landmark_series or []
    effective_fps = float(native_fps) / max(1, int(sample_step))
    window = odd_filter_window(effective_fps)
    if len(frames) < window:
        return None, {
            "valid": False,
            "reason": "shorter_than_filter_window",
            "filter_window": window,
        }
    left_hip_y, right_hip_y = [], []
    raw = {side: [] for side in SIDES}
    for frame in frames:
        lhip, rhip = (
            _point(frame, "left_hip", frame_width, frame_height),
            _point(frame, "right_hip", frame_width, frame_height),
        )
        left_hip_y.append(lhip[0][1] if lhip else np.nan)
        right_hip_y.append(rhip[0][1] if rhip else np.nan)
        for side in SIDES:
            raw[side].append(_signed_fppa(frame, side, frame_width, frame_height))
    valid = [
        all(raw[side][i] is not None for side in SIDES) for i in range(len(frames))
    ]
    hip_mid_y = (np.asarray(left_hip_y) + np.asarray(right_hip_y)) / 2
    if not np.isfinite(hip_mid_y).any():
        return None, {
            "valid": False,
            "reason": "missing_hip_midpoint",
            "filter_window": window,
        }
    bottom_i = int(np.nanargmax(hip_mid_y))
    if not valid[bottom_i]:
        return None, {
            "valid": False,
            "reason": "invalid_bottom_frame",
            "bottom_offset": bottom_i,
            "filter_window": window,
        }
    if sum(valid) / len(valid) < 0.8:
        return None, {
            "valid": False,
            "reason": "insufficient_valid_frames",
            "bottom_offset": bottom_i,
            "filter_window": window,
        }
    for side in SIDES:
        raw[side] = [value if valid[i] else None for i, value in enumerate(raw[side])]
    smoothed = {side: _smooth_valid_runs(raw[side], window) for side in SIDES}
    peaks = {}
    for side in SIDES:
        values = [value for value in smoothed[side] if value is not None]
        peaks[side] = max(values, key=abs)
    features = {
        "fppa_l_bottom": float(smoothed["left"][bottom_i]),
        "fppa_r_bottom": float(smoothed["right"][bottom_i]),
        "fppa_l_peak": float(peaks["left"]),
        "fppa_r_peak": float(peaks["right"]),
    }
    features["asym_bottom"] = abs(features["fppa_l_bottom"] - features["fppa_r_bottom"])
    features["asym_peak"] = abs(features["fppa_l_peak"] - features["fppa_r_peak"])
    return features, {"valid": True, "bottom_offset": bottom_i, "filter_window": window}