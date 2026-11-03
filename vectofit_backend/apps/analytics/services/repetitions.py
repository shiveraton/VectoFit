from apps.assessments.services.video_processor import VideoProcessor

from .pipeline_config import DEFAULT_PREPROCESSING_CONFIG
from .segmentation import _hip_midpoint_y, segment_reps, split_contiguous_pose_runs


def extract_reps(video_path: str) -> dict:
    result = VideoProcessor.process_video(video_path)
    if result.get("status") != "success":
        raise RuntimeError(result.get("message", "Video processing failed."))
    landmark_data = result.get("landmark_data", [])
    if not landmark_data:
        raise RuntimeError("Video processing returned no landmark data.")
    sample_step = int(result["sample_step"])
    runs = split_contiguous_pose_runs(landmark_data, expected_frame_step=sample_step)
    if sum(map(len, runs)) < 3:
        raise RuntimeError("Not enough valid pose frames were produced.")
    reps = []
    for run_number, run in enumerate(runs, start=1):
        if len(run) < 3:
            continue
        segments = segment_reps(
            [entry["landmarks"] for entry in run],
            amplitude_scale=result["processed_frame_height"] / 720.0,
        )
        for segment in segments:
            start, bottom, end = segment["start"], segment["bottom"], segment["end"]
            rep_run = run[start : end + 1]
            raw_hip_y = _hip_midpoint_y([entry["landmarks"] for entry in rep_run])
            bottom = start + int(raw_hip_y.argmax())
            reps.append(
                {
                    "run_number": run_number,
                    "entries": rep_run,
                    "start": run[start]["frame_index"],
                    "bottom": run[bottom]["frame_index"],
                    "end": run[end]["frame_index"],
                    "start_offset": start,
                    "bottom_offset": bottom,
                    "end_offset": end,
                    "key_frame_index": run[bottom]["frame_index"],
                }
            )
    reps.sort(key=lambda rep: (rep["start"], rep["end"]))
    return {
        "result": result,
        "sample_step": sample_step,
        "pose_runs": runs,
        "reps": reps,
        "pipeline_config_hash": DEFAULT_PREPROCESSING_CONFIG.digest(),
    }
