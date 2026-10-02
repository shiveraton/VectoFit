#!/usr/bin/env python3

import cv2
import mediapipe as mp

"""
pose_estimator.py is an abstract lightweight PoseEstimator component reusable across all video feeds.

It contains the following functions:

render_landmarks()
estimate_pose()
"""

mp_pose = mp.solutions.pose

class PoseEstimator:

    SQUAT_JOINTS = {
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
    
    def __init__(self, static_image_mode: bool=False, min_detection_confidence: float=0.5):
        self.static_image_mode = static_image_mode
        self.min_detection_confidence = min_detection_confidence
        self.pose = mp_pose.Pose(static_image_mode=self.static_image_mode, min_detection_confidence=self.min_detection_confidence)

    def estimate_pose(self, frame):
        rgb_frames = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frames)

        return results

    def render_landmarks(self, frame, results):
        mp_drawing = mp.solutions.drawing_utils

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                image=frame,
                landmark_list = results.pose_landmarks,
                connections = mp_pose.POSE_CONNECTIONS
            )

        return frame

    def get_landmark_positions(self, frame, results):
        landmark_list = []
        if results.pose_landmarks:
            # height width channels
            h, w, c = frame.shape

            for id, lm in enumerate(results.pose_landmarks.landmark):
                # calc pixel positions
                cx = int(lm.x * w)
                cy = int(lm.y * h)

                landmark_list.append([id, cx, cy])
                
        return landmark_list

    def get_named_landmarks(self, landmark_list, joint_dict=None):
        if joint_dict is None:
            joint_dict = self.SQUAT_JOINTS
        extracted_coords = {}

        for name, idx in joint_dict.items():
            extracted_coords[name] = [
                landmark_list[idx][1],
                landmark_list[idx][2],
            ]
        return extracted_coords

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

        if (cv2.waitKey(1) & 0xFF == ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()