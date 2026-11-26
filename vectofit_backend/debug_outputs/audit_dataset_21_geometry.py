import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from apps.analytics.services import fppa
from apps.datasets.models import DatasetSample
from apps.training.services.data_loader import _fppa_frames_from_landmark_series, _required_training_frame_rate


snapshot = json.loads(Path("debug_outputs/dataset_21_feature_snapshot.json").read_text())
metadata = {row["sample_id"]: row for row in snapshot["metadata"]}
rows = []
traces = {}
references = defaultdict(list)
raw_frames = []
samples = DatasetSample.objects.filter(pk__in=snapshot["sample_ids"]).select_related(
    "dataset", "dataset_video", "rep_assessment", "rep_assessment__session"
)
for sample in samples.order_by("pk"):
    frames = _fppa_frames_from_landmark_series(sample.rep_assessment.landmark_series)
    width = next((int(f["source_width"]) for f in frames if f.get("source_width")), 1280)
    height = next((int(f["source_height"]) for f in frames if f.get("source_height")), 720)
    fps, timing = _required_training_frame_rate(sample, sample.dataset)
    raw_frames.append({"sample_id": sample.pk, "frames": frames, "width": width, "height": height, "fps": fps})
    features, info = fppa.extract_fppa_features(
        frames, frame_width=width, frame_height=height, native_fps=fps, include_trace=True
    )
    trace = np.asarray([
        [np.nan if x is None else x for x in info["trace"][side]] for side in ("left", "right")
    ])
    side_index, peak_index = np.unravel_index(np.nanargmax(np.abs(trace)), trace.shape)
    side = ("left", "right")[side_index]
    frame = frames[peak_index]
    hip, knee, ankle = [fppa._point(frame, f"{side}_{joint}", width, height)[0] for joint in ("hip", "knee", "ankle")]
    thigh, shank = np.linalg.norm(knee - hip), np.linalg.norm(ankle - knee)
    max_trace = np.max(np.where(np.isnan(trace), -np.inf, np.abs(trace)), axis=0)
    bottom = info["bottom_offset"]
    radius = max(1, round(fps * .15))
    window = trace[:, max(0, bottom - radius):min(len(frames), bottom + radius + 1)]
    peak = float(np.abs(trace[side_index, peak_index]))
    row_meta = metadata[sample.pk]
    hip_y = np.asarray([
        np.mean([fppa._point(f, f"{side}_hip", width, height)[0][1] for side in ("left", "right")])
        if all(fppa._point(f, f"{side}_hip", width, height) is not None for side in ("left", "right")) else np.nan
        for f in frames
    ])
    upright = np.isfinite(hip_y) & np.isfinite(trace).all(axis=0)
    upright &= hip_y <= np.nanquantile(hip_y[upright], .2)
    references[row_meta["participant_id"]].append(np.nanmedian(trace[:, upright], axis=1))
    traces[sample.pk] = (trace, bottom)
    rows.append({
        "sample_id": sample.pk, "source": Path(row_meta["source_path"]).name.split("_")[0],
        "label": row_meta["target"], "peak_degrees": peak,
        "bottom_window_median_max_abs": float(np.nanmax(np.abs(np.nanmedian(window, axis=1)))),
        "fraction_above_25": float(np.mean(max_trace[np.isfinite(max_trace)] > 25)),
        "fraction_above_70": float(np.mean(max_trace[np.isfinite(max_trace)] > 70)),
        "peak_side": side, "peak_offset": int(peak_index), "bottom_offset": bottom,
        "peak_to_bottom_seconds": float(abs(peak_index - bottom) / fps),
        "projected_thigh_to_shank_at_peak": float(thigh / shank),
        "peak_knee_offset_over_projected_leg": float(abs(knee[0] - (hip[0] + (ankle[0] - hip[0]) * (knee[1] - hip[1]) / (ankle[1] - hip[1]))) / (thigh + shank)) if ankle[1] != hip[1] else None,
        "width": width, "height": height, "fps": fps, "timing": timing,
    })
summary = []
for source in ("mdy", "zen"):
    for label in ("good", "bad"):
        subset = [r for r in rows if r["source"] == source and r["label"] == label]
        summary.append({"source": source, "label": label, "count": len(subset), **{
            "median_" + key: float(np.median([r[key] for r in subset]))
            for key in ("peak_degrees", "bottom_window_median_max_abs", "fraction_above_25", "fraction_above_70", "projected_thigh_to_shank_at_peak", "peak_to_bottom_seconds")
        }})
output = Path("debug_outputs/dataset_21_fppa_geometry.json")
output.write_text(json.dumps({"summary": summary, "samples": rows}, indent=2) + "\n")
print(json.dumps(summary, indent=2))
Path("debug_outputs/dataset_21_landmark_snapshot.json").write_text(json.dumps(raw_frames) + "\n")
baselines = {participant: np.median(values, axis=0) for participant, values in references.items()}
normalized_rows = []
for sample_id in snapshot["sample_ids"]:
    meta = metadata[sample_id]
    trace, bottom = traces[sample_id]
    normalized = trace - baselines[meta["participant_id"]][:, None]
    peaks = [float(values[np.nanargmax(np.abs(values))]) for values in normalized]
    bottom_values = normalized[:, bottom].tolist()
    features = dict(zip(("fppa_l_bottom", "fppa_r_bottom"), bottom_values))
    features.update(dict(zip(("fppa_l_peak", "fppa_r_peak"), peaks)))
    features["asym_bottom"] = abs(bottom_values[0] - bottom_values[1])
    features["asym_peak"] = abs(peaks[0] - peaks[1])
    normalized_rows.append([features[name] for name in snapshot["feature_names"]])
snapshot["rows"] = normalized_rows
snapshot["normalization"] = {
    "method": "Subtract participant median signed FPPA reference before computing bottom/peak/asymmetry",
    "reference": "Per-rep most upright 20% of frames by hip midpoint y; median of rep references per participant",
    "limitation": "Upright proxy is not verified standing; uses unlabeled frames from all held-out participant reps (test-time calibration). Not an uncalibrated deployment estimate.",
    "participant_references": {str(p): values.tolist() for p, values in baselines.items()},
}
Path("debug_outputs/dataset_21_normalized_feature_snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n")
