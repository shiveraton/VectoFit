"""Identifies the start/end frame window of each individual squat repetition.

This module defines the ONE-COMPLETED-REPETITION = ONE-ML-SAMPLE invariant. A
repetition is delimited by the hip's descent/ascent cycle, detected on the
midpoint of the left/right hip landmarks.

Input format (shared with the rest of the analytics services):
    landmark_series: list of frames, each a dict mapping landmark name to a
    2-element [x, y] coordinate in pixels, e.g.
        {"left_hip": [512.0, 480.0], "right_hip": [548.0, 482.0], ...}
    (dict-style {"x": .., "y": ..} frames are also accepted.)

Output:
    [{"start": int, "end": int}, ...]  -- end is inclusive, end > start.
"""

import numpy as np

MIN_REP_FRAMES = 5
SMOOTHING_WINDOW = 5


def _hip_midpoint_y(landmark_series):
    """Vertical (y) position of the hip midpoint for every frame."""
    values = []
    for frame in landmark_series:
        left = frame["left_hip"]
        right = frame["right_hip"]
        # index 1 is y for the [x, y] coordinate format used throughout
        # analytics.services. Tolerate dict frames {x:.., y:..} as well.
        left_y = left["y"] if isinstance(left, dict) else left[1]
        right_y = right["y"] if isinstance(right, dict) else right[1]
        values.append((float(left_y) + float(right_y)) / 2.0)
    return np.asarray(values, dtype=float)


def _smooth(signal, window=SMOOTHING_WINDOW):
    """Moving-average smoothing, edge-preserving length via numpy 'same'."""
    if len(signal) < window:
        return signal
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(signal, kernel, mode="same")


def _candidate_extrema(velocity):
    """Frame indices where vertical hip velocity changes sign.

    The squat cycle alternates descending (hip y increasing) and ascending
    (hip y decreasing), so sign changes in the derivative mark the turning
    points (bottom / top of each rep).
    """
    if len(velocity) < 2:
        return []

    signs = np.sign(velocity)
    nonzero = signs[signs != 0]
    if len(nonzero) == 0:
        return []
    signs = signs.copy()
    last = nonzero[0]
    for i in range(len(signs)):
        if signs[i] == 0:
            signs[i] = last
        else:
            last = signs[i]

    sign_changes = np.nonzero(np.diff(signs))[0] + 1
    return sign_changes.tolist()


def segment_reps(landmark_series, min_rep_frames=MIN_REP_FRAMES):
    """Split a landmark series into per-repetition frame windows.

    Returns a list of {"start": int, "end": int} (end inclusive) windows. A
    rep is kept only when it spans at least ``min_rep_frames`` frames, so
    single-frame jitter cannot become an ML sample.
    """
    if not landmark_series:
        return []

    smoothed = _smooth(_hip_midpoint_y(landmark_series))

    if len(smoothed) < min_rep_frames:
        return []

    # Forward-difference derivative: index e corresponds to smoothed[e+1].
    velocity = np.diff(smoothed)
    extrema = _candidate_extrema(velocity)

    if len(extrema) < 2:
        return []

    reps = []
    # Extrema alternate between the bottom and the top of a rep. Pairing them
    # makes each pair span exactly one complete down-and-up cycle.
    for i in range(len(extrema) - 1):
        # Translate derivative indices into landmark-series frame indices.
        start = extrema[i] + 1
        end = extrema[i + 1] + 1

        # A rep window must stay strictly inside the series so the turning
        # points are observed by the segmenter rather than guessed at an edge.
        if start < 1 or end >= len(landmark_series) - 1:
            continue
        if end - start < min_rep_frames:
            continue

        reps.append({"start": int(start), "end": int(end)})

    return reps


def detect_bounce(velocities):
    """Heuristic: flag a rep whose hip velocity reverses more than twice.

    A clean squat reverses once (down then up). Extra reversals indicate the
    lifter bounced at the bottom instead of driving smoothly through it.
    """
    velocities = np.asarray(velocities, dtype=float)
    if len(velocities) < 2:
        return False
    signs = np.sign(velocities)
    signs = signs[signs != 0]
    if len(signs) < 2:
        return False
    sign_changes = np.sum(np.diff(signs) != 0)
    return bool(sign_changes > 2)