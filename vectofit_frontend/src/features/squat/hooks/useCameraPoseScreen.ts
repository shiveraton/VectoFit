import { useCallback, useEffect, useRef, useState } from "react";
import { useIsFocused } from "@react-navigation/native";
import { scheduleOnRN } from "react-native-worklets";
import {
  useCameraDevice,
  useCameraPermission,
  useFrameOutput,
  useVideoOutput,
} from "react-native-vision-camera";
import type { Recorder } from "react-native-vision-camera";

import {
  getAssessmentUploadErrorMessage,
  uploadSquatAssessmentVideo,
} from "../services/assessmentSessionService";
import type {
  AssessmentViewAngle,
  SquatExerciseType,
} from "../../../navigation/types";
import { poseLandmarkerPlugin } from "../../calibration/services/poseLandmarker";

export interface PoseLandmark {
  id: number;
  x_coordinate: number;
  y_coordinate: number;
  z_coordinate: number;
  visibility: number;
}

interface JointAngles {
  hip: number | null;
  knee: number | null;
  ankle: number | null;
}

interface PoseState {
  landmarks: PoseLandmark[];
  isPersonDetected: boolean;
  bodyVisible: boolean;
  confidence: number;
  angles: JointAngles;
  feedback: string;
  frameWidth: number;
  frameHeight: number;
}

type RepPhase = "standing" | "bottom";

const BODY_LANDMARK_INDICES = [0, 11, 12, 23, 24, 25, 26, 27, 28, 31, 32];
const LANDMARKS_PER_POSE = 33;
const VALUES_PER_LANDMARK = 4;
const MIN_LANDMARK_VISIBILITY = 0.3;
const MIN_BODY_VISIBILITY = 0.45;
const MIN_VISIBLE_LANDMARKS = 4;
const MIN_POSE_CONFIDENCE = 0.3;
const UI_UPDATE_INTERVAL_MS = 100;
const SQUAT_BOTTOM_ANGLE = 105;
const SQUAT_STANDING_ANGLE = 155;

const EMPTY_ANGLES: JointAngles = {
  hip: null,
  knee: null,
  ankle: null,
};

const CAMERA_TARGET_RESOLUTION = {
  width: 720,
  height: 1280,
};

const INITIAL_POSE: PoseState = {
  landmarks: [],
  isPersonDetected: false,
  bodyVisible: false,
  confidence: 0,
  angles: EMPTY_ANGLES,
  feedback: "Position your full body in the camera frame.",
  frameWidth: 0,
  frameHeight: 0,
};

function calculateAngle(
  a?: PoseLandmark,
  b?: PoseLandmark,
  c?: PoseLandmark,
): number | null {
  if (!a || !b || !c) return null;

  if (
    a.visibility < MIN_LANDMARK_VISIBILITY ||
    b.visibility < MIN_LANDMARK_VISIBILITY ||
    c.visibility < MIN_LANDMARK_VISIBILITY
  ) {
    return null;
  }

  const angleA = Math.atan2(
    a.y_coordinate - b.y_coordinate,
    a.x_coordinate - b.x_coordinate,
  );
  const angleC = Math.atan2(
    c.y_coordinate - b.y_coordinate,
    c.x_coordinate - b.x_coordinate,
  );

  let degrees = Math.abs(((angleC - angleA) * 180) / Math.PI);
  if (degrees > 180) degrees = 360 - degrees;

  return Math.round(degrees);
}

function flattenLandmarks(values: number[]): PoseLandmark[] {
  if (values.length !== LANDMARKS_PER_POSE * VALUES_PER_LANDMARK) return [];

  return Array.from({ length: LANDMARKS_PER_POSE }, (_, id) => {
    const offset = id * VALUES_PER_LANDMARK;
    return {
      id,
      x_coordinate: values[offset],
      y_coordinate: values[offset + 1],
      z_coordinate: values[offset + 2],
      visibility: values[offset + 3],
    };
  });
}

export function useCameraPoseScreen(
  exercise: SquatExerciseType,
  viewAngle: AssessmentViewAngle,
) {
  const [cameraFacing, setCameraFacing] = useState<"front" | "back">("front");
  const device = useCameraDevice(cameraFacing);
  const { hasPermission, requestPermission } = useCameraPermission();
  const isFocused = useIsFocused();
  const isFocusedRef = useRef(isFocused);
  isFocusedRef.current = isFocused;

  const videoOutput = useVideoOutput({
    enableAudio: false,
    targetResolution: CAMERA_TARGET_RESOLUTION,
  });

  const [pose, setPose] = useState<PoseState>(INITIAL_POSE);
  const [repCount, setRepCount] = useState(0);
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [isRecordingVideo, setIsRecordingVideo] = useState(false);
  const [recordedVideoPath, setRecordedVideoPath] = useState<string | null>(
    null,
  );
  const [recordingError, setRecordingError] = useState<string | null>(null);
  const [isCameraConfigured, setIsCameraConfigured] = useState(false);
  const [isUploadingAssessment, setIsUploadingAssessment] = useState(false);
  const [savedAssessmentMessage, setSavedAssessmentMessage] = useState<
    string | null
  >(null);

  const sessionActiveRef = useRef(false);
  const sessionStartedAtRef = useRef<number | null>(null);
  const repPhaseRef = useRef<RepPhase>("standing");
  const lastUiUpdateRef = useRef(0);
  const processingErrorRef = useRef(false);
  const mountedRef = useRef(true);
  const recordedVideoPathRef = useRef<string | null>(null);
  const cameraConfiguredRef = useRef(false);
  const recorderRef = useRef<Recorder | null>(null);
  const recordingFinishedPromiseRef = useRef<Promise<string | null> | null>(
    null,
  );
  const resolveRecordingRef = useRef<((path: string | null) => void) | null>(
    null,
  );

  const resolveRecording = useCallback((path: string | null) => {
    const resolve = resolveRecordingRef.current;
    resolveRecordingRef.current = null;
    recordingFinishedPromiseRef.current = null;
    resolve?.(path);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      sessionActiveRef.current = false;

      const recorder = recorderRef.current;
      const sessionWasStarted = sessionStartedAtRef.current !== null;
      if (recorder && sessionWasStarted) {
        void recorder.stopRecording().catch((error) => {
          console.error("[SquatRecording] Could not stop on unmount:", error);
        });
      }
    };
  }, []);

  useEffect(() => {
    if (!hasPermission) void requestPermission();
  }, [hasPermission, requestPermission]);

  const handleCameraConfigured = useCallback(() => {
    cameraConfiguredRef.current = true;
    if (mountedRef.current) setIsCameraConfigured(true);
  }, []);

  const handlePoseProcessingError = useCallback(() => {
    if (processingErrorRef.current || !mountedRef.current) return;

    processingErrorRef.current = true;
    setProcessingError(
      "Pose detection failed. Check the camera frame format and native plugin.",
    );
  }, []);

  const handlePoseFrame = useCallback(
    (flattened: number[], frameWidth: number, frameHeight: number) => {
      if (!mountedRef.current) return;

      const landmarks = flattenLandmarks(flattened);
      const now = Date.now();
      const hasPose = landmarks.length === LANDMARKS_PER_POSE;

      if (hasPose && processingErrorRef.current) {
        processingErrorRef.current = false;
        setProcessingError(null);
      }

      const visibleCount = BODY_LANDMARK_INDICES.filter(
        (index) => (landmarks[index]?.visibility ?? 0) >= 0.5,
      ).length;
      const averageConfidence =
        BODY_LANDMARK_INDICES.reduce(
          (sum, index) => sum + (landmarks[index]?.visibility ?? 0),
          0,
        ) / BODY_LANDMARK_INDICES.length;

      const isPersonDetected =
        hasPose &&
        visibleCount >= MIN_VISIBLE_LANDMARKS &&
        averageConfidence >= MIN_POSE_CONFIDENCE;

      const bodyVisible =
        hasPose &&
        BODY_LANDMARK_INDICES.every((index) => {
          const landmark = landmarks[index];
          return (
            landmark !== undefined &&
            landmark.visibility >= MIN_BODY_VISIBILITY &&
            landmark.x_coordinate >= 0.01 &&
            landmark.x_coordinate <= 0.99 &&
            landmark.y_coordinate >= 0.01 &&
            landmark.y_coordinate <= 0.99
          );
        });

      if (!isPersonDetected) {
        repPhaseRef.current = "standing";

        if (now - lastUiUpdateRef.current >= UI_UPDATE_INTERVAL_MS) {
          lastUiUpdateRef.current = now;
          setPose({
            ...INITIAL_POSE,
            landmarks: hasPose ? landmarks : [],
            confidence: averageConfidence,
            frameWidth,
            frameHeight,
            feedback: hasPose
              ? `Pose detected, but confidence is low (${Math.round(
                  averageConfidence * 100,
                )}%). Improve lighting and keep your body visible.`
              : "Move back until your head, knees, ankles, and feet are visible.",
          });
        }
        return;
      }

      const leftScore = [11, 23, 25, 27].reduce(
        (sum, index) => sum + (landmarks[index]?.visibility ?? 0),
        0,
      );
      const rightScore = [12, 24, 26, 28].reduce(
        (sum, index) => sum + (landmarks[index]?.visibility ?? 0),
        0,
      );
      const useLeftSide = leftScore >= rightScore;

      const shoulder = landmarks[useLeftSide ? 11 : 12];
      const hip = landmarks[useLeftSide ? 23 : 24];
      const knee = landmarks[useLeftSide ? 25 : 26];
      const ankle = landmarks[useLeftSide ? 27 : 28];
      const foot = landmarks[useLeftSide ? 31 : 32];

      const angles: JointAngles = {
        hip: calculateAngle(shoulder, hip, knee),
        knee: calculateAngle(hip, knee, ankle),
        ankle: calculateAngle(knee, ankle, foot),
      };

      let feedback = "Move through a controlled squat.";
      if (sessionActiveRef.current && angles.knee !== null) {
        if (angles.knee < SQUAT_BOTTOM_ANGLE) {
          repPhaseRef.current = "bottom";
          feedback = "Bottom position detected. Drive back up.";
        } else if (
          repPhaseRef.current === "bottom" &&
          angles.knee > SQUAT_STANDING_ANGLE
        ) {
          repPhaseRef.current = "standing";
          setRepCount((current) => current + 1);
          feedback = "Rep completed.";
        } else if (repPhaseRef.current === "bottom") {
          feedback = "Return to a standing position.";
        } else {
          feedback = "Lower under control.";
        }
      } else if (!sessionActiveRef.current) {
        feedback = bodyVisible
          ? "Ready. Stand tall and start your session."
          : "Keep your full body visible before starting.";
      } else {
        feedback = "Turn sideways and keep your hip, knee, and ankle visible.";
      }

      if (now - lastUiUpdateRef.current >= UI_UPDATE_INTERVAL_MS) {
        lastUiUpdateRef.current = now;
        setPose({
          landmarks,
          isPersonDetected: true,
          bodyVisible,
          confidence: averageConfidence,
          angles,
          feedback,
          frameWidth,
          frameHeight,
        });
      }
    },
    [],
  );

  const frameOutput = useFrameOutput({
    pixelFormat: "rgb",
    targetResolution: CAMERA_TARGET_RESOLUTION,
    enablePhysicalBufferRotation: true,
    dropFramesWhileBusy: true,
    onFrame(frame) {
      "worklet";
      try {
        const detectedValues = poseLandmarkerPlugin.detect(frame);
        scheduleOnRN(
          handlePoseFrame,
          Array.from(detectedValues),
          frame.width,
          frame.height,
        );
      } catch {
        scheduleOnRN(handlePoseProcessingError);
      } finally {
        frame.dispose();
      }
    },
  });

  const stopSession = useCallback(async (): Promise<string | null> => {
    sessionActiveRef.current = false;
    repPhaseRef.current = "standing";

    const startedAt = sessionStartedAtRef.current;
    if (startedAt !== null && mountedRef.current) {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }

    sessionStartedAtRef.current = null;
    if (mountedRef.current) setIsSessionActive(false);

    const recorder = recorderRef.current;

    if (!recorder) {
      if (mountedRef.current) setIsRecordingVideo(false);
      return recordedVideoPathRef.current;
    }

    const finishedPromise = recordingFinishedPromiseRef.current;

    if (mountedRef.current) {
      setIsUploadingAssessment(true);
      setSavedAssessmentMessage(null);
      setRecordingError(null);
    }

    try {
      await recorder.stopRecording();

      const filePath = finishedPromise ? await finishedPromise : null;

      if (!filePath) {
        throw new Error("Recording stopped, but no video file was returned.");
      }

      try {
        const session = await uploadSquatAssessmentVideo(
          filePath,
          exercise,
          viewAngle,
        );

        const persistedRepCount = session.reps?.length ?? 0;

        console.info("[SquatAssessment] Persisted session:", {
          sessionId: session.id,
          status: session.status,
          persistedRepCount,
        });

        if (mountedRef.current) {
          setRecordingError(null);
          setSavedAssessmentMessage(
            `Assessment #${session.id} saved. Backend detected ${persistedRepCount} rep(s).`,
          );
        }
      } catch (error) {
        const message = getAssessmentUploadErrorMessage(error);

        console.error("[SquatAssessment] Upload or processing failed:", error);

        if (mountedRef.current) {
          setRecordingError(
            `Video recorded locally, but assessment saving failed: ${message}`,
          );
        }
      }

      return filePath;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);

      console.error("[SquatRecording] Could not stop recording:", error);

      if (mountedRef.current) {
        setRecordingError(`Could not finish video recording: ${message}`);
      }

      return null;
    } finally {
      if (recorderRef.current === recorder) {
        recorderRef.current = null;
      }

      if (mountedRef.current) {
        setIsRecordingVideo(false);
        setIsUploadingAssessment(false);
      }
    }
  }, [exercise, viewAngle]);

  const startSession = useCallback(async (): Promise<void> => {
    if (recorderRef.current || sessionActiveRef.current) return;

    if (!isFocusedRef.current || !cameraConfiguredRef.current) {
      setRecordingError("Camera is still preparing. Please try again.");
      return;
    }

    setRecordingError(null);
    setProcessingError(null);
    processingErrorRef.current = false;
    recordedVideoPathRef.current = null;
    setRecordedVideoPath(null);
    setRepCount(0);
    setElapsedSeconds(0);
    repPhaseRef.current = "standing";

    let recorder: Recorder | null = null;
    try {
      recorder = await videoOutput.createRecorder({});
      if (!isFocusedRef.current || !cameraConfiguredRef.current) return;

      recorderRef.current = recorder;
      const finishedPromise = new Promise<string | null>((resolve) => {
        resolveRecordingRef.current = resolve;
      });
      recordingFinishedPromiseRef.current = finishedPromise;

      await recorder.startRecording(
        (filePath, reason) => {
          console.info("[SquatRecording] Video saved:", filePath, reason);
          if (mountedRef.current) {
            recordedVideoPathRef.current = filePath;
            setRecordedVideoPath(filePath);
            setRecordingError(null);
            setIsRecordingVideo(false);
            setIsSessionActive(false);
          }

          const startedAt = sessionStartedAtRef.current;
          if (startedAt !== null && mountedRef.current) {
            setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
          }
          sessionActiveRef.current = false;
          sessionStartedAtRef.current = null;
          if (recorderRef.current === recorder) recorderRef.current = null;
          resolveRecording(filePath);
        },
        (error) => {
          const message =
            error instanceof Error ? error.message : String(error);
          console.error("[SquatRecording] Recording failed:", error);

          if (mountedRef.current) {
            setRecordingError(`Video recording failed: ${message}`);
            setIsRecordingVideo(false);
            setIsSessionActive(false);
          }
          const startedAt = sessionStartedAtRef.current;
          if (startedAt !== null && mountedRef.current) {
            setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
          }
          sessionActiveRef.current = false;
          sessionStartedAtRef.current = null;
          if (recorderRef.current === recorder) recorderRef.current = null;
          resolveRecording(null);
        },
      );

      if (recorderRef.current !== recorder || !isFocusedRef.current) return;

      sessionStartedAtRef.current = Date.now();
      sessionActiveRef.current = true;
      setIsSessionActive(true);
      setIsRecordingVideo(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error("[SquatRecording] Could not start recording:", error);

      if (mountedRef.current) {
        setRecordingError(`Could not start video recording: ${message}`);
        setIsSessionActive(false);
        setIsRecordingVideo(false);
      }
      sessionActiveRef.current = false;
      sessionStartedAtRef.current = null;
      if (recorderRef.current === recorder) recorderRef.current = null;
      resolveRecording(null);
    }
  }, [resolveRecording, videoOutput]);

  const resetSession = useCallback(async (): Promise<void> => {
    await stopSession();

    sessionActiveRef.current = false;
    sessionStartedAtRef.current = null;
    repPhaseRef.current = "standing";

    if (!mountedRef.current) return;
    setIsSessionActive(false);
    setIsRecordingVideo(false);
    setRepCount(0);
    setElapsedSeconds(0);
    recordedVideoPathRef.current = null;
    setRecordedVideoPath(null);
    setRecordingError(null);
  }, [stopSession]);

  const toggleCameraFacing = useCallback(async (): Promise<void> => {
    if (sessionActiveRef.current || recorderRef.current) {
      await stopSession();
    }

    cameraConfiguredRef.current = false;
    setIsCameraConfigured(false);
    setCameraFacing((current) => (current === "front" ? "back" : "front"));
  }, [stopSession]);

  useEffect(() => {
    if (!isSessionActive) return undefined;

    const timer = setInterval(() => {
      const startedAt = sessionStartedAtRef.current;
      if (startedAt !== null) {
        setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [isSessionActive]);

  useEffect(() => {
    if (!isFocused && (sessionActiveRef.current || recorderRef.current)) {
      void stopSession();
    }
  }, [isFocused, stopSession]);

  return {
    exercise,
    device,
    cameraFacing,
    hasPermission,
    requestPermission,
    isCameraActive: isFocused && hasPermission && !!device,
    frameOutput,
    videoOutput,
    pose,
    repCount,
    isSessionActive,
    elapsedSeconds,
    processingError,
    startSession,
    stopSession,
    resetSession,
    toggleCameraFacing,
    handleCameraConfigured,
    isCameraConfigured,
    isRecordingVideo,
    isUploadingAssessment,
    savedAssessmentMessage,
    recordedVideoPath,
    recordingError,
  };
}
