import logging
import math
from collections import Counter
from typing import Any

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)

SMOOTHING_WINDOW = 5
DESPIKE_WINDOW = 5  # median filter: removes 1-2 frame tracking spikes
MIN_PHASE_SECONDS = 0.3
MIN_PHASE_FRAMES = 10  # fallback when fps is unknown
MIN_REP_FRAMES = 2 * MIN_PHASE_FRAMES
MIN_EXCURSION = 35.0  # fallback; prefer a body-relative value
BOUNDARY_FRACTION = 0.10
BASELINE_PERCENTILE = 5  # standing = low-y end of the run (image y grows downward)
STANDING_TOLERANCE_FRACTION = (
    0.5  # valley must be within 0.5 * min_excursion of baseline
)
MIN_PATH_EFFICIENCY = (
    0.6  # net displacement / path length within a phase; tune on real data
)


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


def _landmark_y(landmark) -> float:
    """Extract the vertical coordinate from a landmark representation."""
    if isinstance(landmark, dict):
        return float(landmark["y"])
    return float(landmark[1])


def _hip_midpoint_y(landmark_series) -> np.ndarray:
    """Hip midpoint y per frame; NaN where hip data is unusable (never raises)."""
    out = np.full(len(landmark_series), np.nan)
    for i, frame in enumerate(landmark_series):
        try:
            mid = (
                _landmark_y(frame["left_hip"]) + _landmark_y(frame["right_hip"])
            ) / 2.0
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if np.isfinite(mid):
            out[i] = mid
    return out


def _valid_runs(signal: np.ndarray) -> list[tuple[int, int]]:
    """Half-open [start, end) index ranges of consecutive finite samples."""
    runs: list[tuple[int, int]] = []
    start = None
    for i, ok in enumerate(np.isfinite(signal)):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(signal)))
    return runs


def _smooth(signal, window: int = SMOOTHING_WINDOW) -> np.ndarray:
    """Centered moving average preserving signal length."""
    signal = np.asarray(signal, dtype=float)
    if window <= 1 or len(signal) < window:
        return signal.copy()

    left_pad = (window - 1) // 2
    right_pad = window - 1 - left_pad
    padded = np.pad(signal, (left_pad, right_pad), mode="edge")
    kernel = np.full(window, 1.0 / window, dtype=float)
    return np.convolve(padded, kernel, mode="valid")


def _prepare(raw_run: np.ndarray) -> np.ndarray:
    despiked = median_filter(raw_run, size=DESPIKE_WINDOW, mode="nearest")
    return _smooth(despiked, window=SMOOTHING_WINDOW)


def phase_frames_from_fps(
    effective_fps: float, seconds: float = MIN_PHASE_SECONDS
) -> int:
    """effective_fps = video_fps / frame_step."""
    return max(2, math.ceil(effective_fps * seconds))


def _path_efficiency(seg: np.ndarray) -> float:
    path = float(np.abs(np.diff(seg)).sum())
    return 1.0 if path == 0 else abs(float(seg[-1] - seg[0])) / path


def _descent_onset(s, valley, bottom, frac):
    cut = s[valley] + frac * (s[bottom] - s[valley])
    idx = np.nonzero(s[valley : bottom + 1] <= cut)[0]
    return valley + int(idx[-1])


def _recovery_end(s, bottom, valley, frac):
    cut = s[valley] + frac * (s[bottom] - s[valley])
    idx = np.nonzero(s[bottom : valley + 1] <= cut)[0]
    return bottom + int(idx[0])


def _candidate_bottoms(s, min_excursion, min_phase_frames):
    peaks, _ = find_peaks(
        s, prominence=min_excursion, distance=max(1, min_phase_frames)
    )
    return [int(p) for p in peaks]


def _build_cycle(s, bottoms, k):
    n = len(s)
    bottom = bottoms[k]
    lo = bottoms[k - 1] if k > 0 else 0
    hi = bottoms[k + 1] if k + 1 < len(bottoms) else n - 1
    left_valley = lo + int(np.argmin(s[lo : bottom + 1]))
    right_valley = bottom + int(np.argmin(s[bottom : hi + 1]))
    start = _descent_onset(s, left_valley, bottom, BOUNDARY_FRACTION)
    end = _recovery_end(s, bottom, right_valley, BOUNDARY_FRACTION)
    return start, bottom, end, left_valley, right_valley


def _validate_cycle(
    s,
    start,
    bottom,
    end,
    left_valley,
    right_valley,
    baseline,
    min_excursion,
    min_phase_frames,
    min_rep_frames,
):
    """Return None if valid, else a rejection reason."""
    tol = STANDING_TOLERANCE_FRACTION * min_excursion
    if s[left_valley] - baseline > tol or s[right_valley] - baseline > tol:
        return "not_standing_boundary"
    if min(s[bottom] - s[left_valley], s[bottom] - s[right_valley]) < min_excursion:
        return "amplitude"
    if bottom - start < min_phase_frames or end - bottom < min_phase_frames:
        return "phase_duration"
    if end - start < min_rep_frames:
        return "rep_duration"
    if (
        _path_efficiency(s[start : bottom + 1]) < MIN_PATH_EFFICIENCY
        or _path_efficiency(s[bottom : end + 1]) < MIN_PATH_EFFICIENCY
    ):
        return "discontinuous_phase"
    return None


def _segment_run(s, min_phase_frames, min_rep_frames, min_excursion, rejections):
    if len(s) < min_rep_frames:
        return []

    baseline = float(np.percentile(s, BASELINE_PERCENTILE))
    bottoms = _candidate_bottoms(s, min_excursion, min_phase_frames)

    reps = []
    for k in range(len(bottoms)):
        start, bottom, end, lv, rv = _build_cycle(s, bottoms, k)
        reason = _validate_cycle(
            s,
            start,
            bottom,
            end,
            lv,
            rv,
            baseline,
            min_excursion,
            min_phase_frames,
            min_rep_frames,
        )
        if reason:
            rejections[reason] += 1
        else:
            reps.append({"start": int(start), "bottom": int(bottom), "end": int(end)})
    return reps


def _enforce_invariants(reps):
    """
    Never repairs boundaries. A shared boundary frame (end_i == start_{i+1}) is
    legal for back-to-back squats. Anything else is dropped and logged.
    """
    out = []
    for r in sorted(reps, key=lambda r: r["start"]):
        ok = r["start"] < r["bottom"] < r["end"] and (
            not out or out[-1]["end"] <= r["start"]
        )
        if ok:
            out.append(r)
        else:
            logger.error(
                "[Segmentation] invariant violated, dropping rep %s (prev=%s)",
                r,
                out[-1] if out else None,
            )
    return out


def segment_reps(
    landmark_series,
    min_rep_frames=None,
    min_phase_frames=MIN_PHASE_FRAMES,
    amplitude_scale=1.0,
    min_excursion=None,
):
    """
    Return [{'start','bottom','end'}] as indices into landmark_series.

    min_excursion: absolute threshold in the series' coordinate units. Prefer
    ~0.15-0.20 * median torso length so it is resolution/framing independent.
    Otherwise falls back to MIN_EXCURSION * amplitude_scale.
    """
    if landmark_series is None or len(landmark_series) == 0:
        return []
    if min_phase_frames < 0:
        raise ValueError("min_phase_frames cannot be negative.")
    if min_rep_frames is None:
        min_rep_frames = 2 * min_phase_frames
    if min_rep_frames < 1:
        raise ValueError("min_rep_frames must be at least 1.")
    if min_excursion is None:
        min_excursion = MIN_EXCURSION * float(amplitude_scale)

    raw = _hip_midpoint_y(landmark_series)
    rejections: Counter = Counter()
    reps: list[dict[str, int]] = []

    for run_start, run_end in _valid_runs(raw):
        s = _prepare(raw[run_start:run_end])
        for rep in _segment_run(
            s, min_phase_frames, min_rep_frames, min_excursion, rejections
        ):
            reps.append({k: v + run_start for k, v in rep.items()})

    reps = _enforce_invariants(reps)

    logger.info(
        "[Segmentation] frames=%d invalid=%d reps=%d rejections=%s min_excursion=%.3f phase=%d",
        len(raw),
        int((~np.isfinite(raw)).sum()),
        len(reps),
        dict(rejections),
        min_excursion,
        min_phase_frames,
    )
    return reps


def detect_bounce(velocities):
    """Detect repeated direction reversals in an angular velocity series."""
    velocities = np.asarray(velocities, dtype=float)
    if len(velocities) < 2:
        return False

    signs = np.sign(velocities)
    signs = signs[signs != 0]
    if len(signs) < 2:
        return False

    return bool(np.sum(np.diff(signs) != 0) > 2)
