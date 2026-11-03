import argparse
import csv
import json
import math
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from scipy.signal import savgol_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.analytics.services.preprocessing import apply_clahe
from apps.analytics.services.segmentation import segment_reps
from apps.assessments.services.pose_estimator import PoseEstimator

WINDOW_SECONDS = (0.20, 0.27, 0.33)


def _inventory_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Inventory CSV has no data rows.")
    return rows


def _video_path(root, row):
    filename = next(
        (
            row[key]
            for key in (
                "filename",
                "video",
                "video_file",
                "path",
                "source_path",
                "dataset_video__video_file",
            )
            if row.get(key)
        ),
        None,
    )
    if not filename:
        raise ValueError(
            "Inventory row needs filename, video, video_file, path or source_path."
        )
    candidate = (root / filename).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError(f"Inventory path escapes videos directory: {filename}")
    if not candidate.exists():
        candidate = next(root.rglob(Path(filename).name), candidate)
    return candidate


def _pose_frames(video_path, *, use_clahe, model_complexity, smooth_landmarks):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if not math.isfinite(fps) or fps <= 0:
        cap.release()
        raise RuntimeError(f"Invalid video FPS: {video_path}")
    step = max(1, round(fps / 30.0))
    detector = PoseEstimator(
        model_complexity=model_complexity,
        smooth_landmarks=smooth_landmarks,
        static_image_mode=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        enable_segmentation=False,
    )
    frames, index = [], 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            current = index
            index += 1
            if current % step:
                continue
            processed = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
            if use_clahe:
                processed = apply_clahe(
                    processed, clip_limit=2.0, tile_grid_size=(8, 8)
                )
            result = detector.estimate_pose(processed)
            positions = detector.get_landmark_positions(
                processed, result, coordinate_width=640, coordinate_height=360
            )
            named = detector.get_named_landmarks(positions) if positions else None
            frames.append({"frame_index": current, "landmarks": named})
    finally:
        cap.release()
        detector.close()
    return fps, step, frames


def _detection_summary(frames):
    detected = [frame["landmarks"] for frame in frames if frame["landmarks"]]
    visibilities = [
        point["visibility"] for landmarks in detected for point in landmarks.values()
    ]
    return {
        "sampled_frames": len(frames),
        "detected_frames": len(detected),
        "detection_rate": len(detected) / len(frames) if frames else 0.0,
        "mean_landmark_visibility": float(np.mean(visibilities))
        if visibilities
        else None,
    }


def _fppa(frame, side):
    lm = frame["landmarks"]
    hip, knee, ankle = (
        np.array([lm[f"{side}_{part}"][axis] for axis in ("x", "y")])
        for part in ("hip", "knee", "ankle")
    )
    thigh, shank = knee - hip, ankle - knee
    denom = np.linalg.norm(thigh) * np.linalg.norm(shank)
    if denom == 0:
        return None
    theta = math.degrees(math.acos(float(np.clip(np.dot(thigh, shank) / denom, -1, 1))))
    mid_x = (lm["left_hip"]["x"] + lm["right_hip"]["x"]) / 2
    ankle_line_x = (
        hip[0] + (ankle[0] - hip[0]) * ((knee[1] - hip[1]) / (ankle[1] - hip[1]))
        if ankle[1] != hip[1]
        else hip[0]
    )
    sign = 1 if (knee[0] - ankle_line_x) * np.sign(mid_x - hip[0]) > 0 else -1
    return sign * theta


def _smooth(values, fps, seconds):
    valid = np.asarray(values, dtype=float)
    window = max(1, int(round(fps * seconds)))
    if window % 2 == 0:
        candidates = (window - 1, window + 1)
        window = min(candidates, key=lambda item: abs(item - fps * seconds))
    median = np.asarray(
        [
            np.median(valid[max(0, i - 1) : min(len(valid), i + 2)])
            for i in range(len(valid))
        ]
    )
    if len(median) >= window >= 3:
        return savgol_filter(median, window, 2, mode="interp")
    return median


def _rep_metrics(frames, fps, step):
    groups, group = [], []
    previous = None
    for frame in frames:
        if frame["landmarks"] is None or (
            previous is not None and frame["frame_index"] - previous != step
        ):
            if group:
                groups.append(group)
            group = []
            if frame["landmarks"] is None:
                previous = None
                continue
        group.append(frame)
        previous = frame["frame_index"]
    if group:
        groups.append(group)
    out = []
    effective_fps = fps / step
    for group_index, entries in enumerate(groups, 1):
        reps = segment_reps(
            [entry["landmarks"] for entry in entries], amplitude_scale=360 / 720
        )
        for number, rep in enumerate(reps, 1):
            entry = entries[rep["start"] : rep["end"] + 1]
            series_by_side = {
                side: [_fppa(frame, side) for frame in entry]
                for side in ("left", "right")
            }
            metrics = {
                "run": group_index,
                "rep": number,
                "start_frame": entry[0]["frame_index"],
                "end_frame": entry[-1]["frame_index"],
                "windows": {},
            }
            for seconds in WINDOW_SECONDS:
                window = max(3, int(round(effective_fps * seconds)))
                if window % 2 == 0:
                    window = min(
                        (window - 1, window + 1),
                        key=lambda n: abs(n - effective_fps * seconds),
                    )
                smoothed = {
                    side: _smooth(values, effective_fps, seconds)
                    for side, values in series_by_side.items()
                }
                n = len(entry)
                edge = max(1, int(math.ceil(n * 0.10)))
                jitter = {}
                for side, values in smoothed.items():
                    differences = np.diff(values)
                    jitter[side] = {
                        "first_10pct_std": float(np.std(differences[:edge]))
                        if len(differences[:edge])
                        else 0.0,
                        "last_10pct_std": float(np.std(differences[-edge:]))
                        if len(differences[-edge:])
                        else 0.0,
                    }
                peaks = {
                    side: float(values[int(np.argmax(np.abs(values)))])
                    for side, values in smoothed.items()
                }
                metrics["windows"][f"{seconds:.2f}s"] = {
                    "filter_window": window,
                    "jitter": jitter,
                    "peaks": peaks,
                }
            peak_keys = [metrics["windows"][key]["peaks"] for key in metrics["windows"]]
            metrics["max_peak_change_across_windows"] = {
                side: float(
                    max(values[side] for values in peak_keys)
                    - min(values[side] for values in peak_keys)
                )
                for side in ("left", "right")
            }
            out.append(metrics)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--videos-dir", required=True, type=Path)
    parser.add_argument("--inventory-csv", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("preprocessing_check.json"))
    args = parser.parse_args()
    root = args.videos_dir.resolve()
    rows = _inventory_rows(args.inventory_csv)
    report = {
        "uses_labels_or_models": False,
        "mediapipe_version": mp.__version__,
        "filter_windows_seconds": WINDOW_SECONDS,
        "pose_parameter_comparisons": [],
        "videos": [],
    }
    for complexity in (1, 2):
        for smoothing in (False, True):
            report["pose_parameter_comparisons"].append(
                {"model_complexity": complexity, "smooth_landmarks": smoothing}
            )
    for row in rows:
        path = _video_path(root, row)
        raw_fps, raw_step, raw = _pose_frames(
            path, use_clahe=False, model_complexity=1, smooth_landmarks=True
        )
        clahe_fps, clahe_step, clahe = _pose_frames(
            path, use_clahe=True, model_complexity=1, smooth_landmarks=True
        )
        parameter_runs = []
        for complexity in (1, 2):
            for smoothing in (False, True):
                fps, step, frames = _pose_frames(
                    path,
                    use_clahe=True,
                    model_complexity=complexity,
                    smooth_landmarks=smoothing,
                )
                parameter_runs.append(
                    {
                        "model_complexity": complexity,
                        "smooth_landmarks": smoothing,
                        "detection": _detection_summary(frames),
                        "rep_metrics": _rep_metrics(frames, fps, step),
                    }
                )
        report["videos"].append(
            {
                "video_id": row.get("video_id") or row.get("id") or path.name,
                "filename": str(path.relative_to(root)),
                "raw": _detection_summary(raw),
                "clahe": _detection_summary(clahe),
                "rep_metrics_by_pose_parameters": parameter_runs,
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
