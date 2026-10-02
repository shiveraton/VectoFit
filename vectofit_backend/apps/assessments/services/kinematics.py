#!/usr/bin/env python3

"""
overall kinematics
"""

import numpy as np

def calculate_joint_angle(hip: np.ndarray, knee: np.ndarray, ankle: np.ndarray) -> float:

    vector_a = np.ndarray(hip) - np.array(knee)
    vector_b = np.ndarray(ankle) - np.array(knee)

    cosine_angle = np.dot(vector_a, vector_b) / (
        np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    )

    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)

    angle_rad = np.arccos(cosine_angle)
    return float(np.degrees(angle_rad))

def calculate_angular_velocity(previous_angle: float, current_angle: float, angle_temporal_interval: float) -> float:
    if angle_temporal_interval == 0:
        raise ValueError("angle_temporal_interval must be a non_zero value - check frame timestamp calculation upstream")

    angular_difference = current_angle - previous_angle
    angular_velocity = angular_difference / angle_temporal_interval

    return angular_velocity

def calculate_velocity(previous_position: np.ndarray, current_position: np.ndarray, pose_temporal_interval: float) -> float:
    if pose_temporal_interval == 0:
        raise ValueError("pose_temporal_interval must be a non_zero - check frame timestamp calculation upstream")

    pose_difference = current_position - previous_position
    distance_traveled = np.linalg.norm(pose_difference)
    velocity = distance_traveled / pose_temporal_interval

    return velocity

def calculate_displacement(origin_point: np.ndarray, terminal_point: np.ndarray) -> float:
    displacement = origin_point - terminal_point
    distance_traveled = np.linalg.norm(displacement)

    return distance_traveled