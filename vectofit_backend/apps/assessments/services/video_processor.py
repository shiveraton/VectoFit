#!/usr/bin/env python3

import os
import sys
import cv2
from .pose_estimator import PoseEstimator
from apps.analytics.services.preprocessing import apply_clahe, preprocess_frame
from pathlib import Path

class VideoProcessor:

    @staticmethod
    def initialize_pose_estimator(model_path=None):
        if model_path:
            pose_estimator = PoseEstimator(model_path=model_path)
        else:
            pose_estimator = PoseEstimator()

        return pose_estimator

    @staticmethod
    def open_video_source(video_path):
        cap = cv2.VideoCapture(video_path)

        if not os.path.exists(video_path):
            print(f"File not found at {video_path}")
            return None, None, None

        if not cap.isOpened():
            print(f"Could not open video at {video_path}")
            return None, None, None

        native_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        return cap, native_fps, total_frames

    @staticmethod
    def process_frame(frame, target_width=1280, target_height=720, enable_denoise=False):
        target_resolution = (1280, 720)
        resized_frame = cv2.resize(frame, target_resolution, interpolation=cv2.INTER_AREA) #INTER_CUBIC or INTER_LINEAR to upscale frame smaller than 1280*720

        if enable_denoise:
            enhanced_frame = preprocess_frame(resized_frame)
        else:
            enhanced_frame = apply_clahe(resized_frame)

        return enhanced_frame

    @classmethod
    def process_video(cls, video_path, target_fps=30, enable_denoise=False):
        pose_estimator = cls.initialize_pose_estimator()
        cap, native_fps, total_frames = cls.open_video_source(video_path)

        if cap is None:
            return {"status": "error", "message": "Failed to open video source", "landmarks": []}

        step_size = max(1, round(native_fps / target_fps))
        frame_counter = 0
        extracted_landmark_frames = []

        while cap.isOpened():
            success, raw_frame = cap.read()
            if not success:
                print(f"Unable to read next frame")
                break

            # is a multiple of frame skip step size
            if frame_counter % step_size == 0:
                resized_frame = cls.process_frame(
                    raw_frame,
                    target_width=1280,
                    target_height=720,
                    enable_denoise=enable_denoise
                )

                results = pose_estimator.estimate_pose(resized_frame)

                # Persist the actual landmark coordinates. Previously only the
                # frame index/timestamp was stored, which made every downstream
                # biomechanical computation impossible.
                landmark_positions = pose_estimator.get_landmark_positions(
                    resized_frame, results
                )

                if not landmark_positions:
                    # No pose detected in this frame. Recorded explicitly as
                    # None rather than dropped, so frame indices stay aligned
                    # with the video and the gap is visible downstream.
                    extracted_landmark_frames.append({
                        "frame_index": frame_counter,
                        "timestamp_ms": round((frame_counter / native_fps) * 1000, 2),
                        "landmarks": None,
                    })
                    continue

                named_landmarks = pose_estimator.get_named_landmarks(
                    landmark_positions
                )

                extracted_landmark_frames.append({
                    "frame_index": frame_counter,
                    "timestamp_ms": round((frame_counter / native_fps) * 1000, 2),
                    "landmarks": named_landmarks,
                })

            frame_counter += 1

        cap.release()
        cv2.destroyAllWindows()

        return {
            "status": "success",
            "total_raw_frames": total_frames,
            "processed_frames_count": len(extracted_landmark_frames),
            "native_fps": native_fps,
            "landmark_data": extracted_landmark_frames
        }

    if __name__ == "__main__":
        if len(sys.argv) > 1:
            input_video = sys.argv[1]
        else:
            input_video = "sample.mp4"

        processed = process_video(input_video)
        print(f"Processing complete. Processed {processed} frames.")