import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  LayoutChangeEvent,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import Ionicons from "react-native-vector-icons/Ionicons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Camera } from "react-native-vision-camera";
import { usePreventRemove } from "@react-navigation/native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { RootStackParamList } from "../navigation/types";
import { useCameraPoseScreen } from "../features/squat/hooks/useCameraPoseScreen";
import { useSquatVoice } from "../features/squat/hooks/useSquatVoice";
import PoseLandmarkOverlay from "../features/squat/components/PoseLandmarkOverlay";
import styles, { CAMERA_COLORS } from "../styles/CameraPoseScreenStyles";

type Props = NativeStackScreenProps<RootStackParamList, "CameraPose">;

const EXERCISE_LABELS = {
  bodyweight_squat: "Bodyweight Squat",
  goblet_squat: "Goblet Squat",
  barbell_squat: "Barbell Squat",
} as const;

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

export default function CameraPoseScreen({ route, navigation }: Props) {
  const camera = useCameraPoseScreen(route.params.exercise, "frontal");
  const { width, fontScale } = useWindowDimensions();
  const stackControls = width < 360 || fontScale > 1.2;
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });
  const [cameraError, setCameraError] = useState<string | null>(null);
  const cameraBusy =
    camera.isStartingSession || camera.isSessionActive || camera.isUploadingAssessment;
  const hasUnsavedRecording = Boolean(camera.recordedVideoPath && !camera.savedSession);
  const canStartSession = camera.pose.bodyVisible && camera.isCameraConfigured &&
    !camera.processingError && !cameraError && camera.hasPermission && Boolean(camera.device);
  const voice = useSquatVoice({
    camera,
    canStart: canStartSession && !cameraBusy && !hasUnsavedRecording,
  });

  usePreventRemove(cameraBusy || hasUnsavedRecording, ({ data }) => {
    if (cameraBusy) {
      Alert.alert(
        "Session in progress",
        camera.isSessionActive
          ? "End your session and wait for saving to finish before leaving."
          : "Wait for the current operation to finish before leaving.",
      );
      return;
    }
    Alert.alert(
      "Leave this recording?",
      "This recording is stored temporarily. Check Insights to confirm whether it was saved before leaving.",
      [
        { text: "Stay", style: "cancel" },
        { text: "Leave", style: "destructive", onPress: () => navigation.dispatch(data.action) },
      ],
    );
  });

  const cameraOutputs = useMemo(
    () => [camera.frameOutput, camera.videoOutput],
    [camera.frameOutput, camera.videoOutput],
  );

  const handleViewportLayout = useCallback((event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    setViewportSize((current) =>
      current.width === width && current.height === height ? current : { width, height },
    );
  }, []);

  const openSettings = () => {
    void Linking.openSettings().catch(() => {
      Alert.alert("Open device Settings", "Review VectoFit permissions in your device settings.");
    });
  };

  const openAssessment = () => {
    if (!camera.savedSession) return;
    navigation.popTo("MainTabs", {
      screen: "Insights",
      params: { screen: "SessionResult", params: { sessionId: camera.savedSession.id } },
    });
  };

  const openHistory = () => navigation.popTo("MainTabs", {
    screen: "Insights",
    params: { screen: "SessionHistory" },
  });

  if (!camera.hasPermission || !camera.device) {
    return (
      <SafeAreaView style={styles.center} edges={["top", "bottom"]}>
        <StatusBar barStyle="light-content" />
        <Text style={styles.permissionTitle}>
          {!camera.hasPermission ? "Allow camera access" : "Camera unavailable"}
        </Text>
        <Text style={styles.permissionText}>
          {!camera.hasPermission
            ? "VectoFit uses the camera to record and track your squat movement."
            : "A camera could not be found. Check device camera access and reopen this screen."}
        </Text>
        {!camera.hasPermission ? (
          <Pressable
            style={styles.primaryButton}
            onPress={camera.canRequestPermission ? () => void camera.requestPermission() : openSettings}
            accessibilityRole="button"
          >
            <Text style={styles.primaryButtonText}>
              {camera.canRequestPermission ? "Allow camera" : "Open Settings"}
            </Text>
          </Pressable>
        ) : null}
        <Pressable
          style={styles.secondaryButton}
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
        >
          <Text style={styles.secondaryButtonText}>Go back</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  const { pose } = camera;
  const isSessionButtonDisabled =
    camera.isStartingSession || camera.isUploadingAssessment ||
    (!camera.isSessionActive && (!canStartSession || hasUnsavedRecording));
  let sessionLabel = canStartSession ? "Ready" : "Set up camera";
  if (camera.savedSession) sessionLabel = "Video saved";
  if (camera.isStartingSession) sessionLabel = "Preparing recording";
  if (camera.isSessionActive) sessionLabel = "Recording";
  if (camera.isUploadingAssessment) sessionLabel = "Saving assessment";
  const errorMessage = cameraError || camera.processingError || camera.recordingError;

  const sessionButtonLabel = camera.isUploadingAssessment
    ? "Saving…"
    : camera.isStartingSession
      ? "Preparing…"
      : camera.isSessionActive
        ? "End session"
        : "Start session";

  const discardRecording = () => {
    Alert.alert("Discard this recording?", "You will lose the option to retry saving this video from this screen.", [
      { text: "Cancel", style: "cancel" },
      { text: "Discard", style: "destructive", onPress: () => void camera.resetSession() },
    ]);
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "bottom", "left", "right"]}>
      <StatusBar barStyle="light-content" />
      <View style={styles.topOverlay}>
        <View style={styles.headerRow}>
          <Pressable
            style={({ pressed }) => [
              styles.iconButton,
              pressed && styles.controlPressed,
              cameraBusy && styles.controlDisabled,
            ]}
            disabled={cameraBusy}
            accessibilityRole="button"
            accessibilityLabel="Go back"
            accessibilityState={{ disabled: cameraBusy }}
            onPress={() => navigation.goBack()}
          >
            <Ionicons name="arrow-back" size={22} color={CAMERA_COLORS.text} />
          </Pressable>
          <View style={styles.titleGroup}>
            <Text style={styles.exerciseTitle}>{EXERCISE_LABELS[camera.exercise]}</Text>
            <Text style={styles.supportingText}>Front view assessment</Text>
          </View>
          <Pressable
            style={({ pressed }) => [
              styles.iconButton,
              pressed && styles.controlPressed,
              cameraBusy && styles.controlDisabled,
            ]}
            disabled={cameraBusy}
            onPress={camera.toggleCameraFacing}
            accessibilityRole="button"
            accessibilityLabel="Flip camera"
            accessibilityState={{ disabled: cameraBusy }}
          >
            <Ionicons name="camera-reverse-outline" size={24} color={CAMERA_COLORS.text} />
          </Pressable>
        </View>
      </View>
      <View style={styles.cameraViewport} onLayout={handleViewportLayout}>
        <Camera
          style={StyleSheet.absoluteFill}
          resizeMode="contain"
          implementationMode="compatible"
          device={camera.device}
          isActive={camera.isCameraActive}
          outputs={cameraOutputs}
          onConfigured={() => {
            setCameraError(null);
            camera.handleCameraConfigured();
          }}
          onError={() => setCameraError("Camera interrupted. End any active session, then reopen this screen.")}
        />
        <PoseLandmarkOverlay
          landmarks={pose.landmarks}
          viewportWidth={viewportSize.width}
          viewportHeight={viewportSize.height}
          sourceFrameWidth={pose.frameWidth}
          sourceFrameHeight={pose.frameHeight}
          mirrored={camera.cameraFacing === "front"}
        />
        <View style={styles.previewStatus} pointerEvents="none" accessibilityLiveRegion="polite">
          <View style={[
            styles.statusDot,
            canStartSession && styles.statusDotReady,
            camera.isSessionActive && styles.statusDotRecording,
          ]} />
          <Text style={styles.previewStatusText}>{sessionLabel}</Text>
        </View>
      </View>
      <ScrollView style={styles.bottomOverlay} contentContainerStyle={styles.bottomContent}>
        {errorMessage ? (
          <Text style={styles.errorMessage} accessibilityRole="alert">{errorMessage}</Text>
        ) : (
          <Text style={styles.feedbackText}>
            {camera.isSessionActive
              ? voice.cueMessage || pose.feedback
              : "Face the camera. Keep your head and feet in frame."}
          </Text>
        )}
        {voice.error ? (
          <Text style={styles.errorMessage} accessibilityRole="alert">{voice.error}</Text>
        ) : null}
        {voice.needsSettings ? (
          <Pressable style={styles.secondaryButton} onPress={openSettings} accessibilityRole="button">
            <Text style={styles.secondaryButtonText}>Open voice settings</Text>
          </Pressable>
        ) : null}
        {camera.savedAssessmentMessage ? (
          <Text style={styles.statusText} accessibilityLiveRegion="polite">{camera.savedAssessmentMessage}</Text>
        ) : null}
        <View style={[styles.metricsRow, stackControls && styles.stackedControls]}>
          <View style={styles.repMetric} accessible accessibilityLabel={`Live estimate, ${camera.repCount} repetitions`}>
            <Text style={styles.metricLabel}>Live reps</Text>
            <Text style={styles.repValue}>{camera.repCount}</Text>
          </View>
          <View style={styles.timerMetric}>
            <Text style={styles.metricLabel}>Duration</Text>
            <Text style={styles.timerValue}>{formatTime(camera.elapsedSeconds)}</Text>
          </View>
          <Pressable
            style={styles.voiceControl}
            disabled={voice.isRequestingPermission}
            onPress={() => void voice.toggle()}
            accessibilityRole="switch"
            accessibilityLabel="Voice commands and knee alignment feedback"
            accessibilityHint="Say Start or Stop to control your session"
            accessibilityState={{ checked: voice.enabled, disabled: voice.isRequestingPermission }}
          >
            <Ionicons
              name={voice.enabled ? "mic-outline" : "mic-off-outline"}
              size={20}
              color={voice.enabled ? CAMERA_COLORS.primary : CAMERA_COLORS.textSecondary}
            />
            <View>
              <Text style={styles.voiceLabel}>Voice</Text>
              <Text style={styles.voiceAvailability}>
                {voice.isRequestingPermission ? "Preparing" : voice.isSpeaking ? "Speaking" :
                  voice.isListening ? "Listening" : voice.enabled ? "Paused" : "Off"}
              </Text>
            </View>
          </Pressable>
        </View>
        {voice.enabled ? (
          <Text style={styles.feedbackText}>Say "Start" or "Stop" to control your session.</Text>
        ) : null}
        <Pressable
          style={({ pressed }) => [
            styles.primaryButton,
            pressed && styles.controlPressed,
            camera.isSessionActive && styles.endSessionButton,
            isSessionButtonDisabled && styles.controlDisabled,
          ]}
          disabled={isSessionButtonDisabled}
          onPress={camera.isSessionActive ? () => void camera.stopSession() : () => void camera.startSession()}
          accessibilityRole="button"
          accessibilityState={{
            disabled: isSessionButtonDisabled,
            busy: camera.isStartingSession || camera.isUploadingAssessment,
          }}
        >
          {camera.isStartingSession || camera.isUploadingAssessment ? (
            <ActivityIndicator size="small" color={CAMERA_COLORS.actionText} />
          ) : (
            <Ionicons
              name={camera.isSessionActive ? "stop" : "play"}
              size={18}
              color={CAMERA_COLORS.actionText}
            />
          )}
          <Text style={styles.primaryButtonText}>{sessionButtonLabel}</Text>
        </Pressable>
        {hasUnsavedRecording && !cameraBusy ? (
          <View style={styles.statusRow}>
            {!camera.isUploadUncertain ? (
              <Pressable style={styles.secondaryButton} onPress={() => void camera.retryAssessment()} accessibilityRole="button">
                <Text style={styles.secondaryButtonText}>Retry saving</Text>
              </Pressable>
            ) : null}
            <Pressable style={styles.secondaryButton} onPress={openHistory} accessibilityRole="button">
              <Text style={styles.secondaryButtonText}>Check Insights</Text>
            </Pressable>
            <Pressable style={styles.secondaryButton} onPress={discardRecording} accessibilityRole="button">
              <Text style={styles.secondaryButtonText}>Discard recording</Text>
            </Pressable>
          </View>
        ) : null}
        {camera.savedSession && !cameraBusy ? (
          <Pressable style={styles.secondaryButton} onPress={openAssessment} accessibilityRole="button">
            <Text style={styles.secondaryButtonText}>
              {camera.savedSession.status === "COMPLETED" ? "View results" : "View assessment"}
            </Text>
          </Pressable>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
