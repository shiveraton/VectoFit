from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.assessments.models import AssessmentSession
from apps.assessments.services.video_processor import VideoProcessor

from apps.analytics.services.segmentation import (
    _hip_midpoint_y,
    _smooth,
    _turning_points,
    segment_reps,
    split_contiguous_pose_runs,
)


TARGET_FPS = 30.0


class Command(BaseCommand):
    help = (
        "Reprocess a squat video and plot hip movement and "
        "detected repetition intervals."
    )

    def add_arguments(self, parser):
        parser.add_argument("session_id", type=int)
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Optional output PNG path.",
        )

    def handle(self, *args, **options):
        session_id = options["session_id"]

        try:
            session = AssessmentSession.objects.get(pk=session_id)
        except AssessmentSession.DoesNotExist as exc:
            raise CommandError(
                f"Session {session_id} does not exist."
            ) from exc

        result = VideoProcessor.process_video(session.video_file.path)

        if result.get("status") != "success":
            raise CommandError(
                f"Video processing failed: {result.get('message')}"
            )

        landmark_data = result.get("landmark_data", [])

        if not landmark_data:
            raise CommandError("Video processing returned no landmark data.")

        native_fps = float(result.get("native_fps") or TARGET_FPS)

        if native_fps <= 0:
            native_fps = TARGET_FPS

        expected_frame_step = max(
            1,
            round(native_fps / TARGET_FPS),
        )

        pose_runs = split_contiguous_pose_runs(
            landmark_data,
            expected_frame_step=expected_frame_step,
        )

        valid_frame_count = sum(len(run) for run in pose_runs)

        if valid_frame_count < 3:
            raise CommandError(
                "Not enough valid pose frames to plot."
            )

        fig, ax = plt.subplots(figsize=(16, 7))

        total_tops = 0
        total_bottoms = 0
        rep_traces = []

        first_run = True

        for run_number, run in enumerate(pose_runs, start=1):
            landmarks = [
                entry["landmarks"]
                for entry in run
            ]

            frame_indices = np.asarray(
                [int(entry["frame_index"]) for entry in run],
                dtype=int,
            )

            hip_y = _hip_midpoint_y(landmarks)
            smoothed = _smooth(hip_y)

            bottoms, tops = _turning_points(smoothed)

            total_tops += len(tops)
            total_bottoms += len(bottoms)

            ax.plot(
                frame_indices,
                hip_y,
                alpha=0.35,
                linewidth=0.8,
                label=(
                    "Raw hip midpoint Y"
                    if first_run
                    else None
                ),
            )

            ax.plot(
                frame_indices,
                smoothed,
                linewidth=1.5,
                label=(
                    "Smoothed hip midpoint Y"
                    if first_run
                    else None
                ),
            )

            first_run = False

            if tops:
                ax.scatter(
                    frame_indices[tops],
                    smoothed[tops],
                    marker="^",
                    s=45,
                    label=(
                        "Detected tops"
                        if total_tops == len(tops)
                        else None
                    ),
                    zorder=4,
                )

            if bottoms:
                ax.scatter(
                    frame_indices[bottoms],
                    smoothed[bottoms],
                    marker="v",
                    s=45,
                    label=(
                        "Detected bottoms"
                        if total_bottoms == len(bottoms)
                        else None
                    ),
                    zorder=4,
                )

            if len(run) < 3:
                continue

            segments = segment_reps(landmarks)

            for rep in segments:
                start = rep["start"]
                bottom = rep["bottom"]
                end = rep["end"]

                if not (
                    0 <= start <= bottom <= end < len(run)
                ):
                    self.stderr.write(
                        self.style.WARNING(
                            f"Skipping invalid repetition range "
                            f"in run {run_number}: {rep}"
                        )
                    )
                    continue

                start_frame = int(frame_indices[start])
                bottom_frame = int(frame_indices[bottom])
                end_frame = int(frame_indices[end])

                descent_amplitude = float(
                    smoothed[bottom] - smoothed[start]
                )
                recovery_amplitude = float(
                    smoothed[bottom] - smoothed[end]
                )

                rep_number = len(rep_traces) + 1

                rep_trace = {
                    "number": rep_number,
                    "run": run_number,
                    "start_frame": start_frame,
                    "bottom_frame": bottom_frame,
                    "end_frame": end_frame,
                    "duration": end_frame - start_frame,
                    "descent": descent_amplitude,
                    "recovery": recovery_amplitude,
                }

                rep_traces.append(rep_trace)

                ax.axvspan(
                    start_frame,
                    end_frame,
                    alpha=0.08,
                    label=(
                        "Detected rep intervals"
                        if rep_number == 1
                        else None
                    ),
                )

                ax.axvline(
                    bottom_frame,
                    color="black",
                    alpha=0.35,
                    linestyle=":",
                    linewidth=0.8,
                )

                middle = (start + end) // 2

                ax.annotate(
                    f"R{rep_number}",
                    (
                        frame_indices[middle],
                        smoothed[middle],
                    ),
                    fontsize=8,
                )

        ax.invert_yaxis()
        ax.set_title(
            f"VectoFit Session {session_id}: Full Hip Movement Trace"
        )
        ax.set_xlabel("Original video frame index")
        ax.set_ylabel("Hip midpoint Y coordinate")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best")

        if options["output"]:
            output_path = Path(options["output"])

            if not output_path.is_absolute():
                output_path = Path(settings.BASE_DIR) / output_path
        else:
            output_path = (
                Path(settings.BASE_DIR)
                / "debug_outputs"
                / f"rep_trace_session_{session_id}.png"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=160)
        plt.close(fig)

        self.stdout.write(
            self.style.SUCCESS(f"Plot saved to: {output_path}")
        )

        self.stdout.write(
            f"Original entries: {len(landmark_data)} | "
            f"Valid pose frames: {valid_frame_count} | "
            f"Contiguous pose runs: {len(pose_runs)} | "
            f"Expected frame step: {expected_frame_step}"
        )

        self.stdout.write(
            f"Detected reps: {len(rep_traces)} | "
            f"Turning-point tops: {total_tops} | "
            f"Turning-point bottoms: {total_bottoms}"
        )

        for trace in rep_traces:
            self.stdout.write(
                f"[RepTrace] #{trace['number']:02d} "
                f"run={trace['run']} "
                f"start={trace['start_frame']} "
                f"bottom={trace['bottom_frame']} "
                f"end={trace['end_frame']} "
                f"duration={trace['duration']} "
                f"descent={trace['descent']:.2f} "
                f"recovery={trace['recovery']:.2f}"
            )
