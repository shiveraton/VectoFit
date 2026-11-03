#!/usr/bin/env python3

from typing import ClassVar

import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose


class PoseEstimator:
    SQUAT_JOINTS: ClassVar[dict[str, int]] = {
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_elbow": 13,
        "right_elbow": 14,
        "left_hip": 23,
        "right_hip": 24,
        "left_knee": 25,
        "right_knee": 26,
        "left_ankle": 27,
        "right_ankle": 28,
        "left_heel": 29,
        "right_heel": 30,
    }

    def __init__(
        self,
        static_image_mode: bool = False,
        model_complexity: int = 1,
        smooth_landmarks: bool = True,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        enable_segmentation: bool = False,
    ):
        self.static_image_mode = static_image_mode
        self.min_detection_confidence = min_detection_confidence
        self.model_complexity = model_complexity
        self.smooth_landmarks = smooth_landmarks
        self.min_tracking_confidence = min_tracking_confidence
        self.enable_segmentation = enable_segmentation
        self.pose = mp_pose.Pose(
            static_image_mode=self.static_image_mode,
            model_complexity=self.model_complexity,
            smooth_landmarks=self.smooth_landmarks,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
            enable_segmentation=self.enable_segmentation,
        )

    def estimate_pose(self, frame):
        rgb_frames = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frames)

        return results

    def render_landmarks(self, frame, results):
        mp_drawing = mp.solutions.drawing_utils

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                image=frame,
                landmark_list=results.pose_landmarks,
                connections=mp_pose.POSE_CONNECTIONS,
            )

        return frame

    def get_landmark_positions(
        self,
        frame,
        results,
        coordinate_width=None,
        coordinate_height=None,
    ):
        if not results.pose_landmarks:
            return []

        frame_height, frame_width = frame.shape[:2]
        output_width = coordinate_width or frame_width
        output_height = coordinate_height or frame_height

        return [
            [
                landmark_id,
                float(lm.x * output_width),
                float(lm.y * output_height),
                float(lm.z),
                float(lm.visibility),
                float(lm.x),
                float(lm.y),
            ]
            for landmark_id, lm in enumerate(results.pose_landmarks.landmark)
        ]

    def get_named_landmarks(self, landmark_list, joint_dict=None):
        if joint_dict is None:
            joint_dict = self.SQUAT_JOINTS
        extracted_coords = {}

        for name, idx in joint_dict.items():
            extracted_coords[name] = {
                "x": float(landmark_list[idx][1]),
                "y": float(landmark_list[idx][2]),
                "z": float(landmark_list[idx][3]),
                "visibility": float(landmark_list[idx][4]),
                "x_normalized": float(landmark_list[idx][5]),
                "y_normalized": float(landmark_list[idx][6]),
            }
        return extracted_coords

    def close(self):
        pose = getattr(self, "pose", None)

        if pose is not None:
            self.pose = None
            pose.close()


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    detector = PoseEstimator()

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Camera feed unavailable")
            break

        results = detector.estimate_pose(frame)
        annotated_frame = detector.render_landmarks(frame, results)

        cv2.imshow("Pose Estimation", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
