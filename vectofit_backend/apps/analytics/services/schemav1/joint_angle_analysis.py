import numpy as np


def calculate_joint_angle(hip, knee, ankle) -> float:
    vector_a = np.array(hip) - np.array(knee)
    vector_b = np.array(ankle) - np.array(knee)

    cosine_angle = np.dot(vector_a, vector_b) / (
        np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    )

    angle = np.degrees(np.arccos(cosine_angle))

    return angle


def calculate_angle_series(landmark_series, hip, knee, ankle) -> list:
    angles = []

    for frame in landmark_series:
        hip_point = frame[hip]
        knee_point = frame[knee]
        ankle_point = frame[ankle]

        angle = calculate_joint_angle(hip_point, knee_point, ankle_point)

        angles.append(angle)

    return angles


if __name__ == "__main__":
    print(calculate_joint_angle([0, 1], [0, 0], [1, 0]))

    landmark_series = [
        {
            "left_hip": [0, 1],
            "left_knee": [0, 0],
            "left_ankle": [1, 0],
        },
        {
            "left_hip": [0, 2],
            "left_knee": [0, 0],
            "left_ankle": [2, 0],
        },
    ]

    angles = calculate_angle_series(
        landmark_series,
        "left_hip",
        "left_knee",
        "left_ankle",
    )

    print(angles)
