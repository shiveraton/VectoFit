import numpy as np

def calculate_midpoint(point_a, point_b):
    return (np.array(point_a) + np.array(point_b)) / 2

def calculate_trunk_angle(left_shoulder, right_shoulder, left_hip, right_hip):
    mid_shoulder = calculate_midpoint(left_shoulder, right_shoulder)
    mid_hip = calculate_midpoint(left_hip, right_hip)

    trunk_vector = mid_shoulder - mid_hip
    vertical_vector = np.array([0, -1])

    cosine_angle = np.dot(trunk_vector, vertical_vector) / (
        np.linalg.norm(trunk_vector) * np.linalg.norm(vertical_vector)
    )

    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)

    return float(np.degrees(np.arccos(cosine_angle)))

def calculate_trunk_angle_series(landmark_series):
    angles = []

    for frame in landmark_series:
        angle = calculate_trunk_angle(
            frame["left_shoulder"],
            frame["right_shoulder"],
            frame["left_hip"],
            frame["right_hip"],
        )
        angles.append(angle)

    return angles