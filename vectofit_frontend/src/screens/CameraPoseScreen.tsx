import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  LayoutChangeEvent,
  Pressable,
  StatusBar,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Camera } from "react-native-vision-camera";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import type {
  AssessmentViewAngle,
  RootStackParamList,
} from "../navigation/types";
import { useCameraPoseScreen } from "../features/squat/hooks/useCameraPoseScreen";
import PoseLandmarkOverlay from "../features/squat/components/PoseLandmarkOverlay";
import styles, { CAMERA_COLORS } from "../styles/CameraPoseScreenStyles";

type Props = NativeStackScreenProps<RootStackParamList, "CameraPose">;

const EXERCISE_LABELS = {
  bodyweight_squat: "Bodyweight Squat",
  goblet_squat: "Goblet Squat",
  barbell_squat: "Barbell Squat",
} as const;

const VIEW_ANGLE_OPTIONS: Array<{
  value: AssessmentViewAngle;
  label: string;
}> = [{ value: "frontal", label: "Frontal" }];

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

export default function CameraPoseScreen({ route }: Props) {
  const [viewAngle, setViewAngle] = useState<AssessmentViewAngle>(
    "frontal",
  );
  const camera = useCameraPoseScreen(route.params.exercise, viewAngle);
  const { height: windowHeight } = useWindowDimensions();
  const isCompactScreen = windowHeight < 740;

  const cameraOutputs = useMemo(
    () => [camera.frameOutput, camera.videoOutput],
    [camera.frameOutput, camera.videoOutput],
  );

  const [voiceCuesEnabled, setVoiceCuesEnabled] = useState(false);

  const handleToggleVoiceCues = useCallback(() => {
    setVoiceCuesEnabled((enabled) => !enabled);
  }, []);

  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });

  const handleViewportLayout = useCallback((event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    setViewportSize((current) =>
      current.width === width && current.height === height
        ? current
        : { width, height },
    );
  }, []);

  if (!camera.hasPermission) {
    return (
      <SafeAreaView style={styles.center} edges={["top", "bottom"]}>
        <StatusBar
          barStyle="light-content"
        />
        <Text style={styles.permissionTitle}>
          Camera permission is required
        </Text>
        <Text style={styles.permissionText}>
          VectoFit uses the camera to track your squat movement.
        </Text>
        <Pressable
          style={styles.primaryButton}
          onPress={() => void camera.requestPermission()}
          accessibilityRole="button"
        >
          <Text style={styles.primaryButtonText}>Grant permission</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  if (!camera.device) {
    return (
      <SafeAreaView style={styles.center} edges={["top", "bottom"]}>
        <StatusBar
          barStyle="light-content"
        />
        <ActivityIndicator size="large" color={CAMERA_COLORS.primary} />
        <Text style={styles.permissionText}>Initializing camera…</Text>
      </SafeAreaView>
    );
  }

  const { pose } = camera;
  const canStartSession = pose.bodyVisible && camera.isCameraConfigured;
  const isSessionButtonDisabled =
    camera.isUploadingAssessment ||
    (!camera.isSessionActive && !canStartSession);

  const trackingLabel = pose.bodyVisible
    ? "Full body tracked"
    : pose.isPersonDetected
      ? "Adjust your framing"
      : "Looking for your pose";

  return (
    <SafeAreaView
      style={styles.safeArea}
      edges={["top", "bottom", "left", "right"]}
    >
      <StatusBar
        barStyle="light-content"
      />

      <View style={styles.cameraViewport} onLayout={handleViewportLayout}>
        <Camera
          style={StyleSheet.absoluteFill}
          device={camera.device}
          isActive={camera.isCameraActive}
          outputs={cameraOutputs}
          onConfigured={camera.handleCameraConfigured}
        />

        <PoseLandmarkOverlay
          landmarks={pose.landmarks}
          viewportWidth={viewportSize.width}
          viewportHeight={viewportSize.height}
          sourceFrameWidth={pose.frameWidth}
          sourceFrameHeight={pose.frameHeight}
          mirrored={camera.cameraFacing === "front"}
        />

        <View
          pointerEvents="box-none"
          style={[
            styles.topOverlay,
            isCompactScreen && styles.topOverlayCompact,
          ]}
        >
          <View style={styles.headerRow}>
            <View style={styles.titleGroup}>
              <Text style={styles.eyebrow}>VECTOFIT · LIVE ASSESSMENT</Text>
              <Text
                style={[
                  styles.exerciseTitle,
                  isCompactScreen && styles.exerciseTitleCompact,
                ]}
                numberOfLines={1}
              >
                {EXERCISE_LABELS[camera.exercise]}
              </Text>
            </View>

            <Pressable
              style={({ pressed }) => [
                styles.cameraFlipButton,
                pressed && styles.controlPressed,
                camera.isSessionActive && styles.controlDisabled,
              ]}
              onPress={camera.toggleCameraFacing}
              accessibilityRole="button"
              accessibilityLabel="Flip camera"
              accessibilityHint="Switch between the front and rear cameras"
            >
              <Text style={styles.cameraFlipText}>Flip</Text>
            </Pressable>
          </View>

          <View style={styles.statusRow}>
            <View
              style={[
                styles.trackingPill,
                pose.bodyVisible && styles.trackingPillReady,
                !pose.bodyVisible &&
                  pose.isPersonDetected &&
                  styles.trackingPillWarning,
              ]}
              accessibilityLiveRegion="polite"
            >
              <View
                style={[
                  styles.trackingDot,
                  pose.bodyVisible && styles.trackingDotReady,
                  !pose.bodyVisible &&
                    pose.isPersonDetected &&
                    styles.trackingDotWarning,
                ]}
              />
              <Text style={styles.trackingText}>
                {pose.bodyVisible
                  ? "Full body tracked"
                  : pose.isPersonDetected
                    ? "Adjust your framing"
                    : "Looking for pose"}
              </Text>
            </View>

            <Pressable
              style={[
                styles.voiceCueToggle,
                voiceCuesEnabled && styles.voiceCueToggleActive,
              ]}
              onPress={handleToggleVoiceCues}
              accessibilityRole="switch"
              accessibilityLabel="Voice feedback"
              accessibilityState={{ checked: voiceCuesEnabled }}
              accessibilityHint="Enable or disable spoken exercise feedback"
            >
              <View
                style={[
                  styles.voiceCueDot,
                  voiceCuesEnabled && styles.voiceCueDotActive,
                ]}
              />
              <Text
                style={[
                  styles.voiceCueLabel,
                  voiceCuesEnabled && styles.voiceCueLabelActive,
                ]}
              >
                VOICE {voiceCuesEnabled ? "ON" : "OFF"}
              </Text>
            </Pressable>
          </View>

          <View style={styles.statusRow}>
            <Text style={styles.voiceCueLabel}>ASSESSMENT VIEW</Text>
            {VIEW_ANGLE_OPTIONS.map((option) => (
              <Pressable
                key={option.value}
                onPress={() => setViewAngle(option.value)}
                disabled={camera.isSessionActive || camera.isUploadingAssessment}
                accessibilityRole="button"
                accessibilityState={{ selected: viewAngle === option.value }}
                style={[
                  styles.voiceCueToggle,
                  viewAngle === option.value && styles.voiceCueToggleActive,
                ]}
              >
                <Text
                  style={[
                    styles.voiceCueLabel,
                    viewAngle === option.value && styles.voiceCueLabelActive,
                  ]}
                >
                  {option.label}
                </Text>
              </Pressable>
            ))}
          </View>

          {Boolean(pose.feedback?.trim()) ? (
            <View
              style={[
                styles.feedbackPill,
                isCompactScreen && styles.feedbackPillCompact,
              ]}
              accessibilityLiveRegion="polite"
            >
              <View style={[styles.feedbackGlow]} />
              <Text style={styles.feedbackText} numberOfLines={2}>
                {pose.feedback}
              </Text>
            </View>
          ) : null}
        </View>

        <View
          pointerEvents="box-none"
          style={[
            styles.bottomOverlay,
            isCompactScreen && styles.bottomOverlayCompact,
          ]}
        >
          {camera.processingError || camera.recordingError ? (
            <View style={styles.errorPill} accessibilityRole="alert">
              <Text style={styles.errorMessage}>
                {camera.processingError || camera.recordingError}
              </Text>
            </View>
          ) : null}

          {camera.isUploadingAssessment || camera.savedAssessmentMessage ? (
            <View style={styles.statusPill}>
              {camera.isUploadingAssessment ? (
                <ActivityIndicator size="small" color={CAMERA_COLORS.primary} />
              ) : null}
              <Text style={styles.statusText} numberOfLines={2}>
                {camera.isUploadingAssessment
                  ? "Saving assessment…"
                  : camera.savedAssessmentMessage}
              </Text>
            </View>
          ) : null}

          <View style={styles.bottomHud}>
            <View style={styles.metricsRow}>
              <View style={styles.repMetric}>
                <Text style={styles.metricLabel}>REPS</Text>
                <Text
                  style={[
                    styles.repValue,
                    isCompactScreen && styles.repValueCompact,
                  ]}
                >
                  {camera.repCount}
                </Text>
              </View>

              <View style={styles.metricDivider} />

              <View style={styles.timerMetric}>
                <Text style={styles.metricLabel}>SESSION</Text>
                <Text style={styles.timerValue}>
                  {formatTime(camera.elapsedSeconds)}
                </Text>
              </View>
            </View>

            <Pressable
              style={({ pressed }) => [
                styles.primaryButton,
                camera.isSessionActive && styles.endSessionButton,
                pressed && styles.primaryButtonPressed,
              ]}
              onPress={
                camera.isUploadingAssessment
                  ? undefined
                  : camera.isSessionActive
                    ? camera.stopSession
                    : camera.startSession
              }
              accessibilityRole="button"
              accessibilityLabel={
                camera.isUploadingAssessment
                  ? "Saving assessment"
                  : camera.isSessionActive
                    ? "End squat session"
                    : "Start squat session"
              }
            >
              {camera.isUploadingAssessment ? (
                <ActivityIndicator size="small" color={CAMERA_COLORS.text} />
              ) : null}
              <Text style={styles.primaryButtonText}>
                {camera.isUploadingAssessment
                  ? "Saving…"
                  : camera.isSessionActive
                    ? "End session"
                    : "Start session"}
              </Text>
            </Pressable>
          </View>

          {!camera.isSessionActive &&
          !camera.isUploadingAssessment &&
          !pose.bodyVisible ? (
            <Text style={styles.framingHint} numberOfLines={2}>
              Keep your head and feet in frame. Step back if needed.
            </Text>
          ) : null}
        </View>
      </View>
    </SafeAreaView>
  );
}
