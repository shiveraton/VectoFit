import { useCallback, useEffect, useRef, useState } from "react";
import { useFrameOutput } from "react-native-vision-camera";
import { scheduleOnRN } from "react-native-worklets";

import { validateCalibrationPose } from "../utils/alignmentGuard";
import type { Landmark } from "../utils/alignmentGuard";
import type {
  Landmarks,
  CameraStatus,
  MorphologicalData,
} from "../../../screens/MorphologicalCalibrationScreen";
import type { BodyProfileData } from "../../../navigation/types";
import client from "../../../api/client";
import { poseLandmarkerPlugin } from "../services/poseLandmarker";

export type CalibrationStatus =
  | "idle"
  | "aligning"
  | "holding"
  | "processing"
  | "success"
  | "error";

export interface FrameSize {
  width: number;
  height: number;
}

const REQUIRED_FRAMES = 30;
const IMPORTANT_LANDMARKS = [0, 11, 12, 23, 24, 25, 26, 27, 28, 31, 32];

function averageConfidence(landmarks: Landmark[]): number {
  if (landmarks.length !== 33) return 0;

  return (
    IMPORTANT_LANDMARKS.reduce(
      (sum, index) => sum + (landmarks[index]?.visibility ?? 0),
      0,
    ) / IMPORTANT_LANDMARKS.length
  );
}

function toOverlayLandmarks(raw: Landmark[]): Landmarks | null {
  if (raw.length !== 33) return null;

  return {
    left_shoulder: raw[11],
    right_shoulder: raw[12],
    left_hip: raw[23],
    right_hip: raw[24],
    left_knee: raw[25],
    right_knee: raw[26],
    left_ankle: raw[27],
    right_ankle: raw[28],
  };
}

function readErrorMessage(error: unknown): string {
  const candidate = error as {
    response?: { data?: { detail?: unknown; message?: unknown } };
    message?: unknown;
  };
  const detail = candidate?.response?.data?.detail;
  const message = candidate?.response?.data?.message;

  if (typeof detail === "string" && detail.trim()) return detail;
  if (typeof message === "string" && message.trim()) return message;
  if (typeof candidate?.message === "string" && candidate.message.trim()) {
    return candidate.message;
  }

  return "Calibration failed. Check your framing and try again.";
}

export const useMorphologicalCalibration = (
  bodyProfileData?: BodyProfileData,
) => {
  const [status, setStatus] = useState<CalibrationStatus>("idle");
  const statusRef = useRef<CalibrationStatus>("idle");
  const [feedback, setFeedback] = useState(
    "Stand upright and keep your head and feet in the frame.",
  );
  const [progress, setProgress] = useState(0);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus>({
    camera_is_active: false,
    person_is_detected: false,
    body_fully_visible: false,
    landmark_confidence: 0,
  });
  const [landmarks, setLandmarks] = useState<Landmarks | null>(null);
  const [frameSize, setFrameSize] = useState<FrameSize>({
    width: 0,
    height: 0,
  });
  const [morphologicalData, setMorphologicalData] =
    useState<MorphologicalData | null>(null);

  const frameBuffer = useRef<Landmark[][]>([]);
  const captureRequestedRef = useRef(false);
  const processingRef = useRef(false);
  const lastStatusUpdateRef = useRef(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const transitionTo = useCallback((next: CalibrationStatus) => {
    statusRef.current = next;
    setStatus(next);
  }, []);

  const resetCalibration = useCallback(() => {
    if (processingRef.current) return;

    captureRequestedRef.current = false;
    frameBuffer.current = [];
    setProgress(0);
    setMorphologicalData(null);
    transitionTo("idle");
    setFeedback("Stand upright and keep your head and feet in the frame.");
  }, [transitionTo]);

  const startCalibration = useCallback(() => {
    if (processingRef.current || captureRequestedRef.current) return;

    frameBuffer.current = [];
    captureRequestedRef.current = true;
    setProgress(0);
    setMorphologicalData(null);
    transitionTo("aligning");
    setFeedback(
      "Getting ready. Keep your whole body visible and hold a steady standing pose.",
    );
  }, [transitionTo]);

  const submitCalibrationData = useCallback(
    async (frames: Landmark[][]) => {
      if (processingRef.current || frames.length < REQUIRED_FRAMES) return;

      processingRef.current = true;
      captureRequestedRef.current = false;
      transitionTo("processing");
      setFeedback("Validating measurements and saving your BodyProfile…");

      try {
        const firstFrame = frames[0];
        const averagedLandmarks: Landmark[] = firstFrame.map(
          (_, landmarkIndex) => {
            const totals = frames.reduce(
              (accumulator, frame) => {
                const landmark = frame[landmarkIndex];
                return {
                  x: accumulator.x + landmark.x_coordinate,
                  y: accumulator.y + landmark.y_coordinate,
                  z: accumulator.z + landmark.z_coordinate,
                  visibility: accumulator.visibility + landmark.visibility,
                };
              },
              { x: 0, y: 0, z: 0, visibility: 0 },
            );

            return {
              id: landmarkIndex,
              x_coordinate: totals.x / frames.length,
              y_coordinate: totals.y / frames.length,
              z_coordinate: totals.z / frames.length,
              visibility: totals.visibility / frames.length,
            };
          },
        );

        const response = await client.post("/assessments/calibrate/", {
          body_profile_data: bodyProfileData,
          landmarks: averagedLandmarks,
        });

        const segmentLengths = response.data?.segment_lengths;
        const leftLowerLimb = Number(segmentLengths?.left_femur_cm);
        const rightLowerLimb = Number(segmentLengths?.right_femur_cm);
        const trunk = Number(segmentLengths?.torso_cm);

        if (
          !Number.isFinite(leftLowerLimb) ||
          leftLowerLimb <= 0 ||
          !Number.isFinite(rightLowerLimb) ||
          rightLowerLimb <= 0 ||
          !Number.isFinite(trunk) ||
          trunk <= 0
        ) {
          throw new Error(
            "The server response did not include valid segment measurements, so this screen cannot confirm calibration. Verify the saved profile before retrying.",
          );
        }

        if (!mountedRef.current) return;

        setMorphologicalData({
          left_lower_limb: leftLowerLimb,
          right_lower_limb: rightLowerLimb,
          trunk,
        });
        setProgress(1);
        transitionTo("success");
        setFeedback("The calibration endpoint returned valid measurements.");
      } catch (error) {
        if (!mountedRef.current) return;

        frameBuffer.current = [];
        setProgress(0);
        transitionTo("error");
        setFeedback(readErrorMessage(error));
      } finally {
        processingRef.current = false;
      }
    },
    [bodyProfileData, transitionTo],
  );

  const processFrame = useCallback(
    (rawLandmarks: Landmark[], width: number, height: number) => {
      if (!mountedRef.current) return;

      if (width > 0 && height > 0) {
        setFrameSize((current) =>
          current.width === width && current.height === height
            ? current
            : { width, height },
        );
      }

      const hasPose = rawLandmarks.length === 33;
      const confidence = averageConfidence(rawLandmarks);
      const bodyFullyVisible =
        hasPose &&
        IMPORTANT_LANDMARKS.every((index) => {
          const landmark = rawLandmarks[index];
          return (
            !!landmark &&
            landmark.visibility >= 0.5 &&
            landmark.x_coordinate >= 0.01 &&
            landmark.x_coordinate <= 0.99 &&
            landmark.y_coordinate >= 0.01 &&
            landmark.y_coordinate <= 0.99
          );
        });

      const now = Date.now();
      if (now - lastStatusUpdateRef.current >= 100) {
        lastStatusUpdateRef.current = now;
        setCameraStatus({
          camera_is_active: true,
          person_is_detected: hasPose && confidence >= 0.3,
          body_fully_visible: bodyFullyVisible,
          landmark_confidence: confidence,
        });
      }
      setLandmarks(toOverlayLandmarks(rawLandmarks));

      if (processingRef.current || statusRef.current === "success") return;

      if (!captureRequestedRef.current) {
        if (statusRef.current === "idle") {
          const validation = validateCalibrationPose(rawLandmarks);
          setFeedback(
            !hasPose
              ? "Move into frame and make sure your body is visible."
              : validation.isValid
                ? "Pose detected. Tap Calibrate when you are ready."
                : (validation.reason ?? "Adjust your position in the frame."),
          );
        }
        return;
      }

      if (!hasPose) {
        frameBuffer.current = [];
        transitionTo("aligning");
        setFeedback(
          "No complete pose detected. Show your head, legs, and feet.",
        );
        setProgress(0);
        return;
      }

      const validation = validateCalibrationPose(rawLandmarks);
      if (!validation.isValid) {
        frameBuffer.current = [];
        transitionTo("aligning");
        setFeedback(
          validation.reason ?? "Adjust your position and hold steady.",
        );
        setProgress(0);
        return;
      }

      transitionTo("holding");
      setFeedback("Hold steady while VectoFit records your measurements.");
      frameBuffer.current.push(rawLandmarks);

      const collected = Math.min(frameBuffer.current.length, REQUIRED_FRAMES);
      setProgress(collected / REQUIRED_FRAMES);

      if (frameBuffer.current.length >= REQUIRED_FRAMES) {
        const framesToSubmit = frameBuffer.current.slice(0, REQUIRED_FRAMES);
        frameBuffer.current = [];
        void submitCalibrationData(framesToSubmit);
      }
    },
    [submitCalibrationData, transitionTo],
  );

  const frameOutput = useFrameOutput({
    pixelFormat: "rgb",
    targetResolution: { width: 720, height: 1280 },
    enablePhysicalBufferRotation: true,
    dropFramesWhileBusy: true,
    onFrame(frame) {
      "worklet";

      try {
        const flattened = poseLandmarkerPlugin.detect(frame);
        const rawLandmarks: Landmark[] = [];

        if (flattened.length === 132) {
          for (let index = 0; index < 33; index++) {
            const offset = index * 4;
            rawLandmarks.push({
              id: index,
              x_coordinate: flattened[offset],
              y_coordinate: flattened[offset + 1],
              z_coordinate: flattened[offset + 2],
              visibility: flattened[offset + 3],
            });
          }
        }

        scheduleOnRN(processFrame, rawLandmarks, frame.width, frame.height);
      } catch {
        scheduleOnRN(processFrame, [], frame.width, frame.height);
      } finally {
        frame.dispose();
      }
    },
  });

  return {
    status,
    feedback,
    progress,
    cameraStatus,
    landmarks,
    frameSize,
    morphologicalData,
    startCalibration,
    resetCalibration,
    frameOutput,
  };
};
