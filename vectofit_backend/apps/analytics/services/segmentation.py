import logging
from collections import Counter
from typing import Any

import numpy as np

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
    """
    Split sampled video entries at missing poses or original-frame gaps.

    The entries remain dictionaries containing their original frame_index, so
    callers can segment by local array position and persist the real video
    frame later.
    """
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
    """Extract the vertical coordinate from a landmark representation."""
    if isinstance(landmark, dict):
        return float(landmark["y"])

    return float(landmark[1])


def _hip_midpoint_y(landmark_series):
    """Calculate the vertical midpoint between the left and right hips."""
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
    """Apply a centered moving average while preserving signal length."""
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
    """Find local bottoms and tops using changes in vertical velocity."""
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


def _has_minimum_amplitude(signal, start, end, bottom, threshold):
    """Check whether a top-to-bottom excursion meets the amplitude threshold."""
    return signal[bottom] - signal[start] >= threshold


def _find_cycle_bounds(tops, bottom):
    start = next((top for top in reversed(tops) if top < bottom), None)
    end = next((top for top in tops if top > bottom), None)
    return start, end


def _passes_excursion_checks(
    signal,
    bottom,
    min_rep_frames,
    min_phase_frames,
    start=None,
    end=None,
):
    """Reject bottoms without sufficient descent and recovery amplitude."""
    if start is None or end is None:
        excursion_window = max(2 * min_phase_frames, min_rep_frames)
        left_start = max(0, bottom - excursion_window)
        right_end = min(len(signal), bottom + excursion_window + 1)
    else:
        left_start = int(start)
        right_end = int(end) + 1

    left_values = signal[left_start:bottom]
    right_values = signal[bottom + 1 : right_end]

    if left_values.size == 0 or right_values.size == 0:
        return False

    left_base = left_start + int(np.argmin(left_values))
    right_base = bottom + 1 + int(np.argmin(right_values))

    descent_excursion = signal[bottom] - signal[left_base]
    recovery_excursion = signal[bottom] - signal[right_base]

    return (
        descent_excursion >= MIN_DESCENT_AMPLITUDE
        and recovery_excursion >= MIN_RECOVERY_AMPLITUDE
    )


def _find_repetition_candidates(
    signal,
    bottom,
    tops,
    min_rep_frames,
    min_phase_frames,
):
    """Build complete repetition candidates around valid squat bottoms."""
    repetitions = []
    rejection_counts = Counter()
    candidate_events = []
    seen_bottoms = set()
    start, end = _find_cycle_bounds(tops, bottom)

    if start is None or end is None:
        rejection_counts["missing_boundary"] += 1
        candidate_events.append({
            "bottom": int(bottom),
            "status": "rejeted",
            "reason": "missing_boundary",
        })
        continue

    if (
        bottom - start < min_phase_frames
        or end - bottom < min_phase_frames
    ):
        rejection_counts["phase_duration"]
        candidate_events.append({
            "bottom": int(bottom),
            "start": int(start),
            "end": int(end),
            "status": "rejected",
            "reason": "phase_duration"
        })
        continue

        if not _passes_excursion_checks(
            signal,
            bottom,
            min_rep_frames,
            min_phase_frames,
            start=start,
            end=end,
        ):
            rejection_counts["excursion"] += 1
            candidate_events.append(
                {
                    "bottom": int(bottom),
                    "status": "rejected",
                    "reason": "excursion",
                    "start": int(start),
                    "end": int(end),
                }
            )
            continue

        repetitions.append(
            {
                "start": int(start),
                "bottom": int(bottom),
                "end": int(end),
            }
        )
        candidate_events.append(
            {
                "bottom": int(bottom),
                "status": "accepted",
                "start": int(start),
                "end": int(end),
            }
        )

    return repetitions, rejection_counts, candidate_events


def _repetition_depth_score(repetition, signal):
    """Score a repetition by its vertical excursion depth."""
    start = repetition["start"]
    bottom = repetition["bottom"]
    end = repetition["end"]

    return float(signal[bottom] - max(signal[start], signal[end]))


def _overlap_ratio(first, second):
    """Return overlap length relative to the shorter repetition."""
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
    """Keep the deeper candidate when repetition intervals substantially overlap."""
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
    """
    Segment squat repetitions from hip vertical movement.

    Returned start, bottom, and end values are indices into the supplied
    landmark_series.
    """
    if landmark_series is None or len(landmark_series) == 0:
        return []

    if min_rep_frames < 1:
        raise ValueError("min_rep_frames must be at least 1.")

    if min_phase_frames < 0:
        raise ValueError("min_phase_frames cannot be negative.")

    signal = _smooth(
        _hip_midpoint_y(landmark_series),
        window=SMOOTHING_WINDOW,
    )

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

    logger.info(
        "[Segmentation] %s",
        {
            "frames": len(signal),
            "hip_y_min": round(float(signal.min()), 2),
            "hip_y_max": round(float(signal.max()), 2),
            "hip_y_excursion": round(float(signal.max() - signal.min()), 2),
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
    """Detect repeated direction reversals in an angular velocity series."""
    velocities = np.asarray(velocities, dtype=float)

    if len(velocities) < 2:
        return False

    signs = np.sign(velocities)
    signs = signs[signs != 0]

    if len(signs) < 2:
        return False

    sign_changes = np.sum(np.diff(signs) != 0)

    return bool(sign_changes > 2)
