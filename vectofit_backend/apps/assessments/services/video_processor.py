#!/usr/bin/env python3

import os
import sys
import math
import cv2
from .pose_estimator import PoseEstimator
from apps.analytics.services.preprocessing import (
    apply_clahe, 
    preprocess_frame
)
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
        target_resolution = (target_width, target_height)
        resized_frame = cv2.resize(frame, target_resolution, interpolation=cv2.INTER_AREA) #INTER_CUBIC or INTER_LINEAR to upscale frame smaller than 1280*720

        if enable_denoise:
            enhanced_frame = preprocess_frame(resized_frame)
        else:
            enhanced_frame = apply_clahe(resized_frame)

        return enhanced_frame

    @classmethod
    def process_video(cls, video_path, target_fps=30, enable_denoise=False):
        if not math.isfinite(float(target_fps)) or target_fps <= 0:
            return {
                "status": "error",
                "message": "target_fps must be a positive number.",
                "landmark_data": []
            }

        cap, native_fps, total_frames = cls.open_video_source(
            video_path
        )

        if cap is None:
            return {
                "status": "error", 
                "message": "Failed to open video source", 
                "landmarks": []
            }

        try:
            if not math.isfinite(native_fps) or native_fps <= 0:
                return {
                    "status": "error",
                    "message": (
                        f"Invalid video FPS: {native_fps}. "
                        "Cannot calculate frame timestamps."
                    ),
                    "landmark_data": []
                }

            step_size = max(1, round(native_fps / target_fps))
            frame_counter = 0
            extracted_landmark_frames = []

            pose_estimator = cls.initialize_pose_estimator()

            while cap.isOpened():
                success, raw_frame = cap.read()

                if not success:
                    break

                current_frame_index = frame_counter
                frame_counter += 1

                if current_frame_index % step_size != 0: 
                    continue

                resized_frame = cls.process_frame(
                    raw_frame,
                    target_width=1280,
                    target_height=720,
                    enable_denoise=enable_denoise
                )

                results = pose_estimator.estimate_pose(resized_frame)

                landmark_positions = (
                    pose_estimator.get_landmark_positions(
                        resized_frame, 
                        results
                    )
                )

                timestamp_ms = round(
                    (current_frame_index / native_fps) * 1000, 2
                )

                if not landmark_positions:
                    extracted_landmark_frames.append({
                        "frame_index": current_frame_index,
                        "timestamp_ms": timestamp_ms,
                        "landmarks": None
                    })
                    continue

                named_landmarks = (
                    pose_estimator.get_named_landmarks(
                        landmark_positions
                    )
                )

                extracted_landmark_frames.append({
                    "frame_index": current_frame_index,
                    "timestamp_ms": timestamp_ms,
                    "landmarks": named_landmarks
                })

            pose_detected_count = sum(
                bool(entry.get("landmarks"))
                for entry in extracted_landmark_frames
            )

            return {
                "status": "success",
                "total_raw_frames": total_frames,
                "processed_frames_count": len(extracted_landmark_frames),
                "pose_detected_frames_count": pose_detected_count,
                "native_fps": native_fps,
                "landmark_data": extracted_landmark_frames
            }

        finally:
            cap.release()
    

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_video = sys.argv[1]
    else:
        input_video = "sample.mp4"

    processed = VideoProcessor.process_video(input_video)
    
    print(
        f"Processing status: {processed.get('status')} | "
        f"Sampled frames: {processed.get('processed_frames_count', 0)} | "
        f"Pose-detected frames: "
        f"{processed.get('pose_detected_frames_count', 0)}"
    )

    if processed.get("status") != "success":
        print(processed.get("message", "Video processing failed."))