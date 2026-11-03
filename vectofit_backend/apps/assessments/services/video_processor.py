import logging
import math
import os
import time

import cv2

from apps.analytics.services.pipeline_config import DEFAULT_PREPROCESSING_CONFIG
from apps.analytics.services.preprocessing import apply_clahe, preprocess_frame

from .pose_estimator import PoseEstimator

logger = logging.getLogger(__name__)


class VideoProcessor:
    PROCESSING_WIDTH = DEFAULT_PREPROCESSING_CONFIG.processing_width
    PROCESSING_HEIGHT = DEFAULT_PREPROCESSING_CONFIG.processing_height

    CLAHE_CLIP_LIMIT = DEFAULT_PREPROCESSING_CONFIG.clahe_clip_limit
    CLAHE_TILE_GRID_SIZE = DEFAULT_PREPROCESSING_CONFIG.clahe_tile_grid_size

    @staticmethod
    def initialize_pose_estimator(model_path=None):
        if model_path:
            raise ValueError(
                "Custom model_path is not supported by this MediaPipe PoseEstimator."
            )

        config = DEFAULT_PREPROCESSING_CONFIG
        return PoseEstimator(
            static_image_mode=config.mediapipe_static_image_mode,
            model_complexity=config.mediapipe_model_complexity,
            smooth_landmarks=config.mediapipe_smooth_landmarks,
            min_detection_confidence=config.mediapipe_min_detection_confidence,
            min_tracking_confidence=config.mediapipe_min_tracking_confidence,
            enable_segmentation=config.mediapipe_enable_segmentation,
        )

    @staticmethod
    def open_video_source(video_path):
        if not video_path or not os.path.isfile(video_path):
            logger.error("Video file does not exist: %s", video_path)
            return None, None, None

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            cap.release()
            logger.error("Could not open video: %s", video_path)
            return None, None, None

        native_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        return cap, native_fps, total_frames

    @classmethod
    def process_frame(
        cls,
        frame,
        target_width=PROCESSING_WIDTH,
        target_height=PROCESSING_HEIGHT,
        enable_denoise=False,
        clahe=None,
    ):
        resized_frame = cv2.resize(
            frame,
            (int(target_width), int(target_height)),
            interpolation=cv2.INTER_AREA,
        )

        if enable_denoise:
            return preprocess_frame(resized_frame, clahe=clahe)

        return apply_clahe(resized_frame, clahe=clahe)

    @classmethod
    def process_video(
        cls,
        video_path,
        target_fps=30,
        enable_denoise=False,
        processing_width=PROCESSING_WIDTH,
        processing_height=PROCESSING_HEIGHT,
        coordinate_width=None,
        coordinate_height=None,
    ):
        try:
            target_fps = float(target_fps)
        except (TypeError, ValueError):
            target_fps = 0.0

        if not math.isfinite(target_fps) or target_fps <= 0:
            return {
                "status": "error",
                "message": "target_fps must be a positive number.",
                "landmark_data": [],
            }

        if processing_width <= 0 or processing_height <= 0:
            return {
                "status": "error",
                "message": "Processing width and height must be positive.",
                "landmark_data": [],
            }

        if (coordinate_width is not None and coordinate_width <= 0) or (
            coordinate_height is not None and coordinate_height <= 0
        ):
            return {
                "status": "error",
                "message": "Coordinate width and height must be positive.",
                "landmark_data": [],
            }

        cap, native_fps, total_frames = cls.open_video_source(video_path)

        if cap is None:
            return {
                "status": "error",
                "message": f"Could not open video source: {video_path}",
                "landmark_data": [],
            }

        started_at = time.perf_counter()
        pose_estimator = None

        try:
            if not math.isfinite(native_fps) or native_fps <= 0:
                return {
                    "status": "error",
                    "message": (
                        f"Invalid video FPS: {native_fps}. "
                        "Cannot calculate frame timestamps."
                    ),
                    "landmark_data": [],
                }

            step_size = max(1, round(native_fps / target_fps))
            source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            orientation_property = getattr(cv2, "CAP_PROP_ORIENTATION_META", None)
            rotation_degrees = (
                int(cap.get(orientation_property) or 0)
                if orientation_property is not None
                else 0
            )
            rotation_auto_property = getattr(cv2, "CAP_PROP_ORIENTATION_AUTO", None)
            rotation_auto = (
                bool(cap.get(rotation_auto_property))
                if rotation_auto_property is not None
                else False
            )
            coordinate_width = int(coordinate_width or processing_width)
            coordinate_height = int(coordinate_height or processing_height)
            frame_counter = 0
            extracted_landmark_frames = []

            pose_estimator = cls.initialize_pose_estimator()

            clahe = cv2.createCLAHE(
                clipLimit=cls.CLAHE_CLIP_LIMIT,
                tileGridSize=cls.CLAHE_TILE_GRID_SIZE,
            )

            while True:
                success, raw_frame = cap.read()

                if not success:
                    break

                current_frame_index = frame_counter
                frame_counter += 1

                if current_frame_index % step_size != 0:
                    continue

                processed_frame = cls.process_frame(
                    raw_frame,
                    target_width=processing_width,
                    target_height=processing_height,
                    enable_denoise=enable_denoise,
                    clahe=clahe,
                )

                results = pose_estimator.estimate_pose(processed_frame)

                landmark_positions = pose_estimator.get_landmark_positions(
                    processed_frame,
                    results,
                    coordinate_width=coordinate_width,
                    coordinate_height=coordinate_height,
                )

                timestamp_ms = round(
                    (current_frame_index / native_fps) * 1000,
                    2,
                )

                named_landmarks = (
                    pose_estimator.get_named_landmarks(landmark_positions)
                    if landmark_positions
                    else None
                )

                extracted_landmark_frames.append(
                    {
                        "frame_index": current_frame_index,
                        "timestamp_ms": timestamp_ms,
                        "landmarks": named_landmarks,
                    }
                )

            elapsed_seconds = time.perf_counter() - started_at

            pose_detected_count = sum(
                bool(entry.get("landmarks")) for entry in extracted_landmark_frames
            )
            missing_frame_indices = [
                entry["frame_index"]
                for entry in extracted_landmark_frames
                if not entry.get("landmarks")
            ]
            missing_runs = []
            for entry in extracted_landmark_frames:
                if entry.get("landmarks"):
                    continue
                frame_index = entry["frame_index"]
                if (
                    missing_runs
                    and frame_index == missing_runs[-1]["end_frame"] + step_size
                ):
                    missing_runs[-1]["end_frame"] = frame_index
                    missing_runs[-1]["count"] += 1
                else:
                    missing_runs.append(
                        {
                            "start_frame": frame_index,
                            "end_frame": frame_index,
                            "count": 1,
                        }
                    )

            result = {
                "status": "success",
                "total_raw_frames": total_frames,
                "processed_frames_count": len(extracted_landmark_frames),
                "pose_detected_frames_count": pose_detected_count,
                "native_fps": native_fps,
                "source_width": source_width,
                "source_height": source_height,
                "sample_step": step_size,
                "missing_pose_frames_count": len(missing_frame_indices),
                "missing_runs": missing_runs,
                "landmark_schema_version": "landmarks_v2",
                "processing_width": int(processing_width),
                "processing_height": int(processing_height),
                "coordinate_width": int(coordinate_width),
                "coordinate_height": int(coordinate_height),
                "processed_frame_width": int(processing_width),
                "processed_frame_height": int(processing_height),
                "rotation_metadata_degrees": rotation_degrees,
                "rotation_auto_enabled": rotation_auto,
                "orientation_policy": "opencv_decode_no_additional_rotation",
                "processing_seconds": round(elapsed_seconds, 3),
                "landmark_data": extracted_landmark_frames,
            }

            logger.info(
                "Video pose extraction complete: path=%s "
                "raw_frames=%s sampled_frames=%s pose_frames=%s "
                "valid_pct=%.1f missing_frames=%s missing_indices=%s gap_count=%s "
                "source_resolution=%sx%s processing_resolution=%sx%s elapsed=%.2fs",
                video_path,
                total_frames,
                len(extracted_landmark_frames),
                pose_detected_count,
                (pose_detected_count / len(extracted_landmark_frames) * 100)
                if extracted_landmark_frames
                else 0.0,
                len(missing_frame_indices),
                missing_frame_indices[:20],
                len(missing_runs),
                source_width,
                source_height,
                processing_width,
                processing_height,
                elapsed_seconds,
            )

            return result

        except Exception:
            logger.exception("Video pose extraction failed: %s", video_path)
            raise

        finally:
            cap.release()

            if pose_estimator is not None:
                try:
                    pose_estimator.close()
                except Exception:
                    logger.debug(
                        "Could not close pose estimator cleanly.",
                        exc_info=True,
                    )


if __name__ == "__main__":
    import sys

    input_video = sys.argv[1] if len(sys.argv) > 1 else "sample.mp4"
    processed = VideoProcessor.process_video(input_video)

    print(
        f"Processing status: {processed.get('status')} | "
        f"Sampled frames: {processed.get('processed_frames_count', 0)} | "
        f"Pose-detected frames: {processed.get('pose_detected_frames_count', 0)} | "
        f"Duration: {processed.get('processing_seconds', 0):.2f}s"
    )

    if processed.get("status") != "success":
        print(processed.get("message", "Video processing failed."))
