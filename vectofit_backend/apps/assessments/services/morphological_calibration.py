#!/usr/bin/env python3

# 1. Short and concise
# 2. Specify a return type
# 3. Make as simple and reusable as possible
# 4. Document all your functions

import os
import sys
import cv2
import mediapipe as mp
import math
import numpy as np
import json
from pose_estimator import PoseEstimator
from typing import Any

mp_pose = mp.solutions.pose
pose_detector = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

def calculate_body_data(results) -> dict[str, float]:
    # calculate arms, trunk, hips, legs, knees, ankles

    if not (results and results.pose_world_landmarks):
        return {}

    landmarks = results.pose_world_landmarks.landmark

    def get_dist(idx1: int, idx2: int) -> float:
        p1 = np.array([landmarks[idx1].x, landmarks[idx1].y, landmarks[idx1].z])
        p2 = np.array([landmarks[idx2].x, landmarks[idx2].y, landmarks[idx2].z])
        return float(np.linalg.norm(p1 - p2))

    body_data = {
        "shoulder_width": get_dist(11, 12),
        "hip_width": get_dist(23, 24),
        "left_femur": get_dist(23, 25),
        "right_femur": get_dist(24, 26),
        "left_tibia": get_dist(25, 27),
        "right_tibia": get_dist(26, 28),
    }

    return body_data

def heel_detection(results) -> dict[str, dict[str, float]]:
    # detect left and right heels
    # to be used for heel stability calculation (if moving along with squat movement)

    # returning a dictionary
    # check to see if results exists and if so, if results.pose_landmarks exists
    if not (results and results.pose_landmarks):
        return {}

    landmarks = results.pose_landmarks.landmark
    left_heel = landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value]
    right_heel = landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value]

    return {
        "left_heel": {"x": left_heel.x, "y": left_heel.y, "z": left_heel.z, "vis": left_heel.visibility},
        "right_heel": {"x": right_heel.x, "y": right_heel.y, "z": right_heel.z, "vis": right_heel.visibility},
    }

def calibrate_frame(frame: np.ndarray, pose_estimator: PoseEstimator) -> tuple[np.ndarray, dict[str, any]]:
    # runs estimation, performs calculations, and renders landmarks

    results = pose_estimator.estimate_pose(frame)

    body_data = calculate_body_data(results)
    heel_data = heel_detection(results)

    combined_metrics = {
        "body_data": body_data,
        "heel_data": heel_data
    }

    annotated_frame = pose_estimator.render_landmarks(frame, results)

    return annotated_frame, combined_metrics

def save_custom_body_type(body_data: dict[str, float], user_id: str, output_dir: str = "profiles") -> bool:
    # record calculated body type to use for live feedback later on

    if not body_data:
        return False

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{user_id}_profile.json")

    with open(filepath, "w") as f:
        json.dump(body_data, f, indent=4)

    return True