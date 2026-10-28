import numpy as np

MIN_REP_FRAMES = 5
SMOOTHING_WINDOW = 5
MIN_PHASE_FRAMES = 25
MIN_DESCENT_AMPLITUDE = 35.0
MIN_RECOVERY_AMPLITUDE = 35.0


def _hip_midpoint_y(landmark_series):
    values = []

    for frame in landmark_series:
        left = frame["left_hip"]
        right = frame["right_hip"]

        left_y = left["y"] if isinstance(left, dict) else left[1]
        right_y = right["y"] if isinstance(right, dict) else right[1]

        values.append((float(left_y) + float(right_y)) / 2.0)

    return np.asarray(values, dtype=float)


def _smooth(signal, window=SMOOTHING_WINDOW):
    signal = np.asarray(signal, dtype=float)

    if window <= 1 or len(signal) < window:
        return signal.copy()

    left_pad = (window - 1) // 2
    right_pad = window - 1 - left_pad

    padded = np.pad(
        signal,
        (left_pad, right_pad),
        mode="edge"
    )

    kernel = np.ones(window, dtype=float) / window
    return np.convolve(padded, kernel, mode="valid")


def _turning_points(signal):
    if len(signal) < 3:
        return [], []

    velocity = np.diff(signal)

    bottoms = []
    tops = []

    for frame_index in range(1, len(velocity)):
        previous_velocity = velocity[frame_index - 1]
        current_velocity = velocity[frame_index]

        if previous_velocity > 0 and current_velocity <= 0:
            bottoms.append(frame_index)

        elif previous_velocity < 0 and current_velocity >= 0:
            tops.append(frame_index)

    return bottoms, tops


def segment_reps(landmark_series, min_rep_frames=MIN_REP_FRAMES, min_phase_frames=MIN_PHASE_FRAMES):
    if not landmark_series:
        return []

    smoothed = _smooth(_hip_midpoint_y(landmark_series))

    if len(smoothed) < min_rep_frames:
        return []

    bottoms, tops = _turning_points(smoothed)

    if not bottoms or not tops:
        return []

    events = []

    for top in tops:
        events.append((top, "top"))

    for bottom in bottoms:
        events.append((bottom, "bottom"))

    events.sort(key=lambda event: event[0])

    repetitions = []

    initial_window = min(5, len(smoothed))

    if initial_window >= 2:
        x = np.arange(initial_window)
        initial_slope = np.polyfit(
            x,
            smoothed[:initial_window],
            1,
        )[0]
    else:
        initial_slope = 0.0

    if initial_slope > 0:
        start = 0
        bottom = None
        expected = "bottom"
    else:
        start = None
        bottom=None
        expected = "top"

    for frame_index, event_type in events:

        if expected == "top":
            if event_type == "top":
                start = frame_index
                expected = "bottom"

        elif expected == "bottom":
            if event_type == "bottom":
                if frame_index - start >= min_phase_frames:
                    bottom = frame_index
                    expected = "end"

        elif expected == "end":
            if event_type == "top":
                if frame_index - bottom >= min_phase_frames:
                    end = frame_index

                    if end - start >= min_rep_frames:
                        descent_amplitude = (smoothed[bottom] - smoothed[start])
                        recovery_amplitude = (smoothed[bottom] -smoothed[end])

                        if (descent_amplitude >= MIN_DESCENT_AMPLITUDE and recovery_amplitude >= MIN_RECOVERY_AMPLITUDE):
                            repetitions.append(
                                {
                                    "start": int(start),
                                    "bottom": int(bottom),
                                    "end": int(end)
                                }
                            )

                            start = frame_index
                            bottom = None
                            expected = "bottom"

                            return repetitions

def detect_bounce(velocities):
    velocities = np.asarray(velocities, dtype=float)

    if len(velocities) < 2:
        return False

    signs = np.sign(velocities)
    signs = signs[signs != 0]

    if len(signs) < 2:
        return False

    sign_changes = np.sum(np.diff(signs) != 0)

    return bool(sign_changes > 2)