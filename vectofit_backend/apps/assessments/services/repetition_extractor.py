import logging
from itertools import pairwise
from typing import Any

from apps.analytics.services.segmentation import (
    segment_reps,
    split_contiguous_pose_runs,
)

logger = logging.getLogger(__name__)


def _split_contiguous_pose_runs(
    landmark_data: list[dict[str, Any]],
    expected_frame_step: int,
) -> list[list[dict[str, Any]]]:
    return split_contiguous_pose_runs(
        landmark_data,
        expected_frame_step,
    )


def collect_repetition_entries(
    session_id: int,
    landmark_data: list[dict[str, Any]],
    expected_frame_step: int,
) -> list[dict[str, Any]]:
    pose_runs = _split_contiguous_pose_runs(
        landmark_data,
        expected_frame_step=expected_frame_step,
    )

    repetition_entries: list[dict[str, Any]] = []

    run_gaps = [
        (previous[-1]["frame_index"], current[0]["frame_index"])
        for previous, current in pairwise(pose_runs)
    ]
    logger.info(
        "[RepCount] session=%s pose_runs=%s run_lengths=%s run_ranges=%s gaps=%s",
        session_id,
        len(pose_runs),
        [len(run) for run in pose_runs],
        [(run[0]["frame_index"], run[-1]["frame_index"]) for run in pose_runs],
        run_gaps,
    )

    for run_index, run in enumerate(pose_runs, start=1):
        if len(run) < 3:
            continue

        landmark_series = [entry["landmarks"] for entry in run]

        repetitions = segment_reps(landmark_series)

        logger.info(
            "[RepCount] session=%s run=%s frames=%s reps=%s",
            session_id,
            run_index,
            len(run),
            len(repetitions),
        )

        for repetition in repetitions:
            try:
                start_index = int(repetition["start"])
                bottom_index = int(repetition["bottom"])
                end_index = int(repetition["end"])
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"Invalid repetition boundaries: {repetition}"
                ) from exc

            if not (0 <= start_index <= bottom_index <= end_index < len(run)):
                raise RuntimeError(f"Invalid repetition range: {repetition}")

            rep_entries = run[start_index : end_index + 1]

            if rep_entries:
                repetition_entries.append(
                    {
                        "entries": rep_entries,
                        "key_frame_index": rep_entries[bottom_index - start_index][
                            "frame_index"
                        ],
                    }
                )

    if not repetition_entries:
        raise RuntimeError("No complete squat repetitions were detected.")

    return repetition_entries
