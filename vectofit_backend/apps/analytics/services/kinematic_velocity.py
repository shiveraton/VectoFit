import numpy as np
from apps.assessments.services.kinematics import calculate_velocity

# velocity = positional distance traveled / time interval


def calculate_velocity_series(landmark_series, landmark_name, time_interval):
    velocities = []

    for i in range(1, len(landmark_series)):
        previous_position = landmark_series[i - 1][landmark_name]
        current_position = landmark_series[i][landmark_name]

        velocity = calculate_velocity(
            np.array(previous_position), np.array(current_position), time_interval
        )

        velocities.append(velocity)

    return velocities


if __name__ == "__main__":
    landmark_series = [
        {"left_knee": [100, 200]},
        {"left_knee": [105, 210]},
        {"left_knee": [110, 220]},
        {"left_knee": [120, 240]},
    ]

    velocities = calculate_velocity_series(landmark_series, "left_knee", 0.1)

    print(velocities)
