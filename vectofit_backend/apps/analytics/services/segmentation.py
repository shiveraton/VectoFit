import logging
from collections import Counter
from typing import Any

import numpy as np
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)

MIN_REP_FRAMES = 5
SMOOTHING_WINDOW = 5
MIN_PHASE_FRAMES = 10
MIN_DESCENT_AMPLITUDE = 35.0
MIN_RECOVERY_AMPLITUDE = 35.0

DUPLICATE_OVERLAP_THRESHOLD = 0.50


def split_contiguous_pose_runs(
    landmark_data: list[dict[str, Any]],
    expected_frame_step: int,
) -> list[list[dict[str, Any]]]:
    if expected_frame_step < 1:
        raise ValueError("expected_frame_step must be at least 1.")

    runs: list[list[dict[str, Any]]] = []
    current_run: list[dict[str, Any]] = []
    previous_frame_index: int | None = None

    for entry in landmark_data:
        landmarks = entry.get("landmarks")
        raw_frame_index = entry.get("frame_index")

        if not landmarks or raw_frame_index is None:
            if current_run:
                runs.append(current_run)
            current_run = []
            previous_frame_index = None
            continue

        frame_index = int(raw_frame_index)

        if (
            current_run
            and previous_frame_index is not None
            and frame_index - previous_frame_index != expected_frame_step
        ):
            runs.append(current_run)
            current_run = []

        current_run.append(entry)
        previous_frame_index = frame_index

    if current_run:
        runs.append(current_run)

    return runs


def _landmark_y(landmark):
    if isinstance(landmark, dict):
        return float(landmark["y"])

    return float(landmark[1])


def _hip_midpoint_y(landmark_series):
    values = []

    for frame_index, frame in enumerate(landmark_series):
        try:
            left_y = _landmark_y(frame["left_hip"])
            right_y = _landmark_y(frame["right_hip"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid hip landmarks at frame {frame_index}.") from exc

        midpoint = (left_y + right_y) / 2.0

        if not np.isfinite(midpoint):
            raise ValueError(f"Non-finite hip midpoint at frame {frame_index}.")

        values.append(midpoint)

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
        mode="edge",
    )

    kernel = np.full(window, 1.0 / window, dtype=float)

    return np.convolve(
        padded,
        kernel,
        mode="valid",
    )


def _turning_points(signal):
    if len(signal) < 3:
        return [], []

    velocity = np.diff(signal)
    moving = np.flatnonzero(np.abs(velocity) > 1e-9)
    bottoms = []
    tops = []
    if not len(moving):
        return bottoms, tops

    first, last = int(moving[0]), int(moving[-1])
    if first > 0 and velocity[first] > 0:
        tops.append(first)

    for previous, current in zip(moving, moving[1:]):
        turning = int((previous + 1 + current) // 2)
        if velocity[previous] < 0 and velocity[current] > 0:
            tops.append(turning)

    if last < len(velocity) - 1 and velocity[last] < 0:
        tops.append(last + 1)

    bottoms = find_peaks(
        signal,
        prominence=min(MIN_DESCENT_AMPLITUDE, MIN_RECOVERY_AMPLITUDE),
    )[0].tolist()
    boundaries = [-1, *bottoms, len(signal)]
    cycle_tops = []
    for start, end in zip(boundaries, boundaries[1:]):
        candidates = [top for top in tops if start < top < end]
        if candidates:
            cycle_tops.append(min(candidates, key=lambda top: signal[top]))

    return bottoms, cycle_tops


def _find_cycle_bounds(tops, bottom):
    start = next((top for top in reversed(tops) if top < bottom), None)
    end = next((top for top in tops if top > bottom), None)
    return start, end


def _passes_excursion_checks(signal, start, bottom, end):
    descent_values = signal[int(start) : bottom]
    recovery_values = signal[bottom + 1 : int(end) + 1]

    if descent_values.size == 0 or recovery_values.size == 0:
        return False

    descent_excursion = signal[bottom] - descent_values.min()
    recovery_excursion = signal[bottom] - recovery_values.min()

    return (
        descent_excursion >= MIN_DESCENT_AMPLITUDE
        and recovery_excursion >= MIN_RECOVERY_AMPLITUDE
    )


def _rejection_reason(signal, start, bottom, end, min_rep_frames, min_phase_frames):
    if start is None or end is None:
        return "missing_boundary"
    if bottom - start < min_phase_frames or end - bottom < min_phase_frames:
        return "phase_duration"
    if end - start < min_rep_frames:
        return "duration"
    if not _passes_excursion_checks(signal, start, bottom, end):
        return "excursion"
    return None


def _find_repetition_candidates(
    signal,
    bottoms,
    tops,
    min_rep_frames,
    min_phase_frames,
):
    repetitions = []
    rejection_counts = Counter()
    candidate_events = []
    seen_bottoms = set()

    for bottom in bottoms:
        if bottom in seen_bottoms:
            continue

        seen_bottoms.add(bottom)
        start, end = _find_cycle_bounds(tops, bottom)

        reason = _rejection_reason(
            signal,
            start,
            bottom,
            end,
            min_rep_frames,
            min_phase_frames,
        )

        event = {
            "bottom": int(bottom),
            "start": int(start) if start is not None else None,
            "end": int(end) if end is not None else None,
        }

        if reason is not None:
            rejection_counts[reason] += 1
            candidate_events.append({**event, "status": "rejected", "reason": reason})
            continue

        repetitions.append(event)
        candidate_events.append({**event, "status": "accepted"})

    return repetitions, rejection_counts, candidate_events


def _repetition_depth_score(repetition, signal):
    start = repetition["start"]
    bottom = repetition["bottom"]
    end = repetition["end"]

    return float(signal[bottom] - max(signal[start], signal[end]))


def _overlap_ratio(first, second):
    overlap = max(
        0,
        min(first["end"], second["end"]) - max(first["start"], second["start"]) + 1,
    )

    first_length = first["end"] - first["start"] + 1
    second_length = second["end"] - second["start"] + 1

    shorter_length = min(first_length, second_length)

    if shorter_length <= 0:
        return 0.0

    return overlap / shorter_length


def _deduplicate_repetitions(repetitions, signal):
    ordered = sorted(
        repetitions,
        key=lambda repetition: (
            repetition["start"],
            repetition["end"],
        ),
    )

    unique_repetitions = []

    for candidate in ordered:
        duplicate_index = None

        for index, existing in enumerate(unique_repetitions):
            if _overlap_ratio(candidate, existing) >= DUPLICATE_OVERLAP_THRESHOLD:
                duplicate_index = index
                break

        if duplicate_index is None:
            unique_repetitions.append(candidate)
            continue

        existing = unique_repetitions[duplicate_index]

        if _repetition_depth_score(candidate, signal) > _repetition_depth_score(
            existing, signal
        ):
            unique_repetitions[duplicate_index] = candidate

    return sorted(
        unique_repetitions,
        key=lambda repetition: repetition["start"],
    )


def segment_reps(
    landmark_series,
    min_rep_frames=MIN_REP_FRAMES,
    min_phase_frames=MIN_PHASE_FRAMES,
):
    if landmark_series is None or len(landmark_series) == 0:
        return []

    if min_rep_frames < 1:
        raise ValueError("min_rep_frames must be at least 1.")

    if min_phase_frames < 0:
        raise ValueError("min_phase_frames cannot be negative.")

    hip_midpoints = _hip_midpoint_y(landmark_series)
    signal = _smooth(hip_midpoints, window=SMOOTHING_WINDOW)

    if len(signal) < min_rep_frames:
        return []

    bottoms, tops = _turning_points(signal)

    if not bottoms or not tops:
        return []

    repetitions, rejection_counts, candidate_events = _find_repetition_candidates(
        signal=signal,
        bottoms=bottoms,
        tops=tops,
        min_rep_frames=min_rep_frames,
        min_phase_frames=min_phase_frames,
    )

    repetitions = _deduplicate_repetitions(repetitions, signal)
    hip_y_min = float(signal.min())
    hip_y_max = float(signal.max())

    logger.info(
        "[Segmentation] %s",
        {
            "frames": len(signal),
            "hip_y_min": round(hip_y_min, 2),
            "hip_y_max": round(hip_y_max, 2),
            "hip_y_excursion": round(hip_y_max - hip_y_min, 2),
            "turning_points": {"bottoms": len(bottoms), "tops": len(tops)},
            "rejection_counts": dict(rejection_counts),
            "candidate_events": candidate_events,
            "repetitions": repetitions,
            "constraints": {
                "min_rep_frames": min_rep_frames,
                "min_phase_frames": min_phase_frames,
                "min_descent_amplitude": MIN_DESCENT_AMPLITUDE,
                "min_recovery_amplitude": MIN_RECOVERY_AMPLITUDE,
                "smoothing_window": SMOOTHING_WINDOW,
            },
        },
    )

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
