import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StatusBar,
  Text,
  TouchableOpacity,
  View,
  useWindowDimensions,
} from "react-native";
import type { LayoutChangeEvent } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  useCameraDevice,
  useCameraPermission,
} from "react-native-vision-camera";
import { useIsFocused } from "@react-navigation/native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import type { BodyProfileData, RootStackParamList } from "../navigation/types";
import { useMorphologicalCalibration } from "../features/calibration/hooks/useMorphologicalCalibration";
import type { FrameSize } from "../features/calibration/hooks/useMorphologicalCalibration";

import { CalibrationCamera } from "../components/morphology/CalibrationCamera";
import { LandmarkOverlay } from "../components/morphology/LandmarkOverlay";
import { CalibrationProgress } from "../components/morphology/CalibrationProgress";
import { CalibrationResult } from "../components/morphology/CalibrationResult";
import styles, {
  CALIBRATION_COLORS,
} from "../styles/MorphologicalCalibrationScreenStyles";

type Props = NativeStackScreenProps<
  RootStackParamList,
  "MorphologicalCalibration"
>;

export type CalibrationPosition = "front" | "side" | "45_degree";

export type CalibrationStatus =
  | "idle"
  | "aligning"
  | "holding"
  | "processing"
  | "success"
  | "error";

export interface CameraStatus {
  camera_is_active: boolean;
  person_is_detected: boolean;
  body_fully_visible: boolean;
  landmark_confidence: number;
}

export interface Landmark {
  x_coordinate: number;
  y_coordinate: number;
  z_coordinate: number;
  visibility: number;
}

export interface Landmarks {
  left_shoulder: Landmark;
  right_shoulder: Landmark;
  left_hip: Landmark;
  right_hip: Landmark;
  left_knee: Landmark;
  right_knee: Landmark;
  left_ankle: Landmark;
  right_ankle: Landmark;
}

export interface MorphologicalData {
  left_lower_limb: number;
  right_lower_limb: number;
  trunk: number;
}

interface ViewPortSize {
  width: number;
  height: number;
}

const POSITION_OPTIONS: Array<{
  value: CalibrationPosition;
  label: string;
  accessibilityLabel: string;
}> = [
  { value: "front", label: "FRONT", accessibilityLabel: "Front view" },
  { value: "side", label: "SIDE", accessibilityLabel: "Side view" },
  { value: "45_degree", label: "45°", accessibilityLabel: "45 degree view" },
];

function hasValidBodyProfile(
  profile?: BodyProfileData | null,
): profile is BodyProfileData {
  if (!profile) return false;

  return [
    profile.shoulder_width,
    profile.hip_width,
    profile.left_femur,
    profile.right_femur,
    profile.left_tibia,
    profile.right_tibia,
  ].every((value) => Number.isFinite(value) && value > 0);
}

function isBusy(status: CalibrationStatus) {
  return status === "processing";
}

export default function MorphologicalCalibrationScreen({
  route,
  navigation,
}: Props) {
  const passedBodyProfileData = route.params?.bodyProfileData;
  const bodyProfileData = hasValidBodyProfile(passedBodyProfileData)
    ? passedBodyProfileData
    : undefined;

  const [cameraFacing, setCameraFacing] = useState<"front" | "back">("front");
  const [calibrationPosition, setCalibrationPosition] =
    useState<CalibrationPosition>("front");
  const [viewportSize, setViewportSize] = useState<ViewPortSize>({
    width: 0,
    height: 0,
  });

  const { height: windowHeight } = useWindowDimensions();
  const isCompactScreen = windowHeight < 760;
  const device = useCameraDevice(cameraFacing);
  const { hasPermission, requestPermission } = useCameraPermission();
  const isFocused = useIsFocused();

  const {
    status,
    feedback,
    progress,
    cameraStatus,
    landmarks,
    morphologicalData,
    startCalibration,
    resetCalibration,
    frameOutput,
    frameSize,
  } = useMorphologicalCalibration(bodyProfileData);

  useEffect(() => {
    if (!hasPermission) {
      void requestPermission();
    }
  }, [hasPermission, requestPermission]);

  const isCapturing = status === "aligning" || status === "holding";
  const isProcessing = isBusy(status);
  const isHolding = status === "holding";
  const isSuccessful = status === "success" && Boolean(morphologicalData);

  const hasExistingProfile = useMemo(
    () =>
      hasValidBodyProfile(bodyProfileData) ||
      morphologicalData !== null ||
      status === "error",
    [bodyProfileData, morphologicalData, status],
  );

  const trackingLabel = cameraStatus.body_fully_visible
    ? "Full body visible"
    : cameraStatus.person_is_detected
      ? "Person detected · step back"
      : "Keep head and feet in frame";

  const handleToggleCameraFacing = useCallback(() => {
    if (isCapturing || isProcessing) return;
    setCameraFacing((current) => (current === "front" ? "back" : "front"));
  }, [isCapturing, isProcessing]);

  const requestCalibration = useCallback(() => {
    if (!hasPermission || !device) {
      Alert.alert(
        "Camera not ready",
        "Grant camera access and wait for the preview to initialize.",
      );
      return;
    }

    if (hasExistingProfile) {
      Alert.alert(
        "Recalibrate BodyProfile?",
        "A valid body profile or a previous calibration attempt may exist. Continuing may replace stored measurements. Cancel to preserve the current state.",
        [
          { text: "Cancel", style: "cancel" },
          {
            text: "Continue",
            style: "destructive",
            onPress: startCalibration,
          },
        ],
      );
      return;
    }

    startCalibration();
  }, [device, hasExistingProfile, hasPermission, startCalibration]);

  const handlePositionChange = useCallback(
    (position: CalibrationPosition) => {
      if (isProcessing || position === calibrationPosition) return;
      setCalibrationPosition(position);
      if (status !== "success") resetCalibration();
    },
    [calibrationPosition, isProcessing, resetCalibration, status],
  );

  const handleCyclePosition = useCallback(() => {
    if (isCapturing || isProcessing) return;

    const currentIndex = POSITION_OPTIONS.findIndex(
      (option) => option.value === calibrationPosition,
    );

    const nextOption =
      POSITION_OPTIONS[(currentIndex + 1) % POSITION_OPTIONS.length];

    setCalibrationPosition(nextOption.value);

    if (status !== "success") {
      resetCalibration();
    }
  }, [
    calibrationPosition,
    isCapturing,
    isProcessing,
    resetCalibration,
    status,
  ]);

  const currentPosition =
    POSITION_OPTIONS.find((option) => option.value === calibrationPosition) ??
    POSITION_OPTIONS[0];

  const handleStageLayout = useCallback((event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    setViewportSize((current) =>
      current.width === width && current.height === height
        ? current
        : { width, height },
    );
  }, []);

  if (!hasPermission) {
    return (
      <SafeAreaView style={styles.centerContent} edges={["top", "bottom"]}>
        <StatusBar
          barStyle="light-content"
        />
        <Text style={styles.permissionTitle}>Camera permission needed</Text>
        <Text style={styles.emptyStateText}>
          VectoFit needs camera access to detect your pose and calibrate body
          measurements.
        </Text>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => void requestPermission()}
          accessibilityRole="button"
        >
          <Text style={styles.actionButtonText}>Grant permission</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  if (!device) {
    return (
      <SafeAreaView style={styles.centerContent} edges={["top", "bottom"]}>
        <StatusBar
          barStyle="light-content"
        />
        <ActivityIndicator size="large" color={CALIBRATION_COLORS.primary} />
        <Text style={styles.emptyStateText}>Initializing camera…</Text>
      </SafeAreaView>
    );
  }

  const frame: FrameSize = frameSize;

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
      <StatusBar
        barStyle="light-content"
      />

      <View style={styles.screen}>
        <View style={styles.cameraStage} onLayout={handleStageLayout}>
          <CalibrationCamera
            device={device}
            isActive={isFocused && hasPermission}
            frameOutput={frameOutput}
            containerStyle={styles.cameraFill}
          >
            <LandmarkOverlay
              landmarks={landmarks}
              isValid={isHolding || status === "success"}
              viewportWidth={viewportSize.width}
              viewportHeight={viewportSize.height}
              frameWidth={frame.width}
              frameHeight={frame.height}
              mirrored={cameraFacing === "front"}
            />

            <View
              style={[
                styles.topOverlay,
                isCompactScreen && styles.topOverlayCompact,
              ]}
              pointerEvents="box-none"
            >
              <View style={styles.headerRow}>
                <View style={styles.titleGroup}>
                  <Text style={styles.eyebrow}>VECTOFIT · BODY PROFILE</Text>
                  <Text style={styles.screenTitle} numberOfLines={1}>
                    Morphological Calibration
                  </Text>
                </View>
              </View>

              {/*
              <View style={styles.positionSelectorContainer}>
                {POSITION_OPTIONS.map((option) => {
                  const isSelected = calibrationPosition === option.value;
                  return (
                    <TouchableOpacity
                      key={option.value}
                      style={[
                        styles.positionPill,
                        isSelected && styles.positionPillActive,
                      ]}
                      onPress={() => handlePositionChange(option.value)}
                      disabled={isProcessing}
                      accessibilityRole="button"
                      accessibilityLabel={option.accessibilityLabel}
                      accessibilityState={{ selected: isSelected }}
                    >
                      <Text
                        style={[
                          styles.positionPillText,
                          isSelected && styles.positionPillTextActive,
                        ]}
                      >
                        {option.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View> */}
            </View>

            <View
              style={[
                styles.bottomOverlay,
                isCompactScreen && styles.bottomOverlayCompact,
              ]}
              pointerEvents="box-none"
            >
              <View style={styles.statusPillsRow}>
                <View
                  style={[
                    styles.trackingPill,
                    cameraStatus.body_fully_visible && styles.trackingPillReady,
                    !cameraStatus.body_fully_visible &&
                      cameraStatus.person_is_detected &&
                      styles.trackingPillWarning,
                  ]}
                  accessibilityLiveRegion="polite"
                >
                  <View
                    style={[
                      styles.statusDot,
                      cameraStatus.body_fully_visible && styles.statusDotGood,
                      !cameraStatus.body_fully_visible &&
                        cameraStatus.person_is_detected &&
                        styles.statusDotWarning,
                    ]}
                  />
                  <Text style={styles.statusPillText} numberOfLines={1}>
                    {trackingLabel}
                  </Text>
                </View>

                <View style={styles.confidencePill}>
                  <Text style={styles.confidenceText}>
                    {Math.round(cameraStatus.landmark_confidence * 100)}% pose
                  </Text>
                </View>
              </View>

              {isCapturing || isProcessing ? (
                <View style={styles.progressWrapper}>
                  <View style={styles.progressTextRow}>
                    <Text style={styles.progressLabel}>
                      {isProcessing
                        ? "Saving measurements…"
                        : isHolding
                          ? "Hold still"
                          : "Aligning pose"}
                    </Text>
                    <Text style={styles.progressPercent}>
                      {Math.round(progress * 100)}%
                    </Text>
                  </View>
                  <CalibrationProgress progress={progress} />
                </View>
              ) : null}

              {status === "success" && morphologicalData ? (
                <CalibrationResult
                  data={morphologicalData}
                  onContinue={() => navigation.goBack()}
                  onRetry={requestCalibration}
                />
              ) : (
                <View style={styles.actionRow}>
                  <TouchableOpacity
                    style={[
                      styles.angleSwitcherButton,
                      (isCapturing || isProcessing) &&
                        styles.actionButtonDisabled,
                    ]}
                    onPress={handleCyclePosition}
                    disabled={isCapturing || isProcessing}
                    accessibilityRole="button"
                    accessibilityLabel={`Camera angle: ${currentPosition.accessibilityLabel}. Tap to switch angle`}
                    accessibilityHint="Cycles between front, side, and 45 degree views"
                  >
                    <Text style={styles.angleSwitcherEyebrow}>VIEW</Text>
                    <Text style={styles.angleSwitcherText}>
                      {currentPosition.label}
                    </Text>
                  </TouchableOpacity>

                  {isCapturing ? (
                    <TouchableOpacity
                      style={[
                        styles.actionButton,
                        styles.secondaryActionButton,
                      ]}
                      onPress={resetCalibration}
                      disabled={isProcessing}
                      accessibilityRole="button"
                    >
                      <Text style={styles.actionButtonText}>Cancel</Text>
                    </TouchableOpacity>
                  ) : (
                    <TouchableOpacity
                      style={[
                        styles.actionButton,
                        isProcessing && styles.actionButtonDisabled,
                      ]}
                      onPress={requestCalibration}
                      disabled={isProcessing}
                      accessibilityRole="button"
                    >
                      {isProcessing ? (
                        <ActivityIndicator color={CALIBRATION_COLORS.text} />
                      ) : (
                        <Text style={styles.actionButtonText}>
                          {status === "error" ? "Try again" : "Calibrate"}
                        </Text>
                      )}
                    </TouchableOpacity>
                  )}
                </View>
              )}

              {!isCapturing &&
              !isProcessing &&
              !isSuccessful &&
              status !== "error" &&
              !cameraStatus.body_fully_visible ? (
                <Text style={styles.framingHint} numberOfLines={2}>
                  Step back until your head and feet are visible.
                </Text>
              ) : null}
            </View>
          </CalibrationCamera>
        </View>
      </View>
    </SafeAreaView>
  );
}
