from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

SKELETON_CONNECTIONS: tuple[tuple[str, str], ...] = (
    ("left_shoulder", "left_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_shoulder", "right_hip"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
)
LANDMARK_SPACE = (1280.0, 720.0)
REFERENCE_LANDMARK_IDS = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}


def _point(value: Any, width: int, height: int) -> tuple[int, int] | None:
    if isinstance(value, dict):
        x, y = (
            value.get("x", value.get("x_coordinate")),
            value.get("y", value.get("y_coordinate")),
        )
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        x, y = value[0], value[1]
    else:
        return None
    try:
        x, y = float(x), float(y)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    x *= width / LANDMARK_SPACE[0]
    y *= height / LANDMARK_SPACE[1]
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    return max(0, min(width - 1, round(x))), max(0, min(height - 1, round(y)))


def normalize_landmarks(
    raw: Any, width: int, height: int
) -> dict[str, tuple[int, int]]:
    if isinstance(raw, dict) and "landmarks" in raw:
        raw = raw["landmarks"]
    if not isinstance(raw, dict):
        return {}
    return {
        str(name): point
        for name, value in raw.items()
        if (point := _point(value, width, height)) is not None
    }


def draw_skeleton(
    frame: np.ndarray,
    landmarks: Any,
    color: tuple[int, int, int],
    *,
    thickness: int = 4,
    dashed: bool = False,
) -> bool:
    height, width = frame.shape[:2]
    points = normalize_landmarks(landmarks, width, height)
    drawn = False
    for start, end in SKELETON_CONNECTIONS:
        if start not in points or end not in points:
            continue
        if dashed:
            cv2.line(frame, points[start], points[end], color, thickness, cv2.LINE_AA)
        else:
            cv2.line(frame, points[start], points[end], color, thickness, cv2.LINE_AA)
        drawn = True
    for point in points.values():
        cv2.circle(frame, point, max(4, thickness + 1), color, -1, cv2.LINE_AA)
        drawn = True
    return drawn


def reference_landmarks(rep: Any) -> Any:
    analysis_result = rep.analysis_result
    if not isinstance(analysis_result, dict):
        return None
    template = analysis_result.get("reference_template")
    if not isinstance(template, dict):
        return None
    if template.get("coordinate_space") != "1280x720":
        return None
    if template.get("view_angle") not in (None, rep.session.view_angle):
        return None
    return template.get("landmarks")


def reference_template_from_profile(
    profile: Any,
    view_angle: str | None,
    squat_landmarks: Any = None,
) -> dict[str, Any] | None:
    """Build a body-aware reference in snapshot coordinates.

    Calibration is intentionally captured in a standing pose, so using those
    coordinates directly makes the reference skeleton stand over every squat.
    When a representative squat frame is available, retain its joint
    directions and place the calibrated segment lengths along those directions.
    The standing calibration remains a safe fallback for older assessments.
    """
    raw = getattr(profile, "raw_calibration_data", None)
    if not isinstance(raw, list):
        return None

    by_id = {}
    for index, landmark in enumerate(raw):
        if not isinstance(landmark, dict):
            continue
        try:
            landmark_id = int(landmark.get("id", index))
            x = float(landmark["x_coordinate"])
            y = float(landmark["y_coordinate"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(x) and math.isfinite(y):
            by_id[landmark_id] = (x, y)

    calibrated = {}
    for name, landmark_id in REFERENCE_LANDMARK_IDS.items():
        point = by_id.get(landmark_id)
        if point is None:
            return None
        x, y = point
        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
            x *= LANDMARK_SPACE[0]
            y *= LANDMARK_SPACE[1]
        calibrated[name] = np.array([x, y], dtype=float)

    landmarks = calibrated

    if isinstance(squat_landmarks, dict):
        observed = {}
        for name in REFERENCE_LANDMARK_IDS:
            value = squat_landmarks.get(name)
            if isinstance(value, dict):
                x = value.get("x", value.get("x_coordinate"))
                y = value.get("y", value.get("y_coordinate"))
            elif isinstance(value, (list, tuple)) and len(value) >= 2:
                x, y = value[0], value[1]
            else:
                continue
            try:
                point = np.array([float(x), float(y)], dtype=float)
            except (TypeError, ValueError):
                continue
            if np.isfinite(point).all():
                observed[name] = point

        if len(observed) == len(REFERENCE_LANDMARK_IDS):
            def place_segment(
                start: np.ndarray,
                observed_start: np.ndarray,
                observed_end: np.ndarray,
                length: float,
            ) -> np.ndarray:
                direction = observed_end - observed_start
                norm = float(np.linalg.norm(direction))
                if norm <= 1e-6 or not math.isfinite(norm):
                    return start.copy()
                return start + direction / norm * length

            torso_length = float(
                np.linalg.norm(
                    calibrated["left_shoulder"] - calibrated["left_hip"]
                )
            )
            left_femur = float(
                np.linalg.norm(calibrated["left_hip"] - calibrated["left_knee"])
            )
            right_femur = float(
                np.linalg.norm(calibrated["right_hip"] - calibrated["right_knee"])
            )
            left_tibia = float(
                np.linalg.norm(calibrated["left_knee"] - calibrated["left_ankle"])
            )
            right_tibia = float(
                np.linalg.norm(calibrated["right_knee"] - calibrated["right_ankle"])
            )

            squat = {
                "left_ankle": observed["left_ankle"],
                "right_ankle": observed["right_ankle"],
            }
            for side in ("left", "right"):
                ankle = f"{side}_ankle"
                knee = f"{side}_knee"
                hip = f"{side}_hip"
                squat[knee] = place_segment(
                    squat[ankle], observed[ankle], observed[knee],
                    left_tibia if side == "left" else right_tibia,
                )
                squat[hip] = place_segment(
                    squat[knee], observed[knee], observed[hip],
                    left_femur if side == "left" else right_femur,
                )
                squat[f"{side}_shoulder"] = place_segment(
                    squat[hip], observed[hip], observed[f"{side}_shoulder"],
                    torso_length,
                )
            landmarks = squat

    return {
        "coordinate_space": "1280x720",
        "view_angle": view_angle,
        "landmarks": {
            name: {"x": float(point[0]), "y": float(point[1])}
            for name, point in landmarks.items()
        },
    }
