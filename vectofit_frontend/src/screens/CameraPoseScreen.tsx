import React, { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import styles from "../styles/CameraPoseScreenStyles";
import { RootStackParamList } from "../navigation/types";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { AppText } from "../components/AppText";

// Camera Preview | DONE
// Start / Stop Recording | DONE
// Exercise Status & Feedback | DONE
// Rep Counter | DONE
// 45° Angle Alignment Guide (Rule-Based) | NEED TO DO
// MediaPipe Landmark Overlay | NEED TO DO
// Session Timer | NEED TO DO

type CameraPoseScreenProps = NativeStackScreenProps<
  RootStackParamList,
  "CameraPose"
>;

interface SquatSession {
  is_recording: boolean;
  squat_type: string;
  rep_count: number;
  instant_feedback: string;
  quality_assessment: string;
}

interface CameraStatus {
  landmark: string;
  angle: string;
}

interface Landmark {
  x_coordinate: number;
  y_coordinate: number;
  z_coordinate: number;
  visibility: number; //mediapipe confidence
}

interface PoseFrame {
  landmarks: Landmark[];
  timestamp: number;
}

interface SquatMetrics {
  hip_angle: number;
  knee_angle: number;
  ankle_angle: number;
  depth: number;
  symmetry: number;
  velocity: number;
}

export default function CameraPoseScreen({ route }: CameraPoseScreenProps) {
  const [squat_session] = useState<SquatSession>({
    is_recording: false,
    squat_type: "",
    rep_count: 0,
    instant_feedback: "",
    quality_assessment: "",
  });

  const [camera_status] = useState<CameraStatus>({
    landmark: "",
    angle: "",
  });

  const [landmark] = useState({
    x_coordinate: 0,
    y_coordinate: 0,
    z_coordinate: 0,
    visibility: 0,
  });

  const [pose_frame] = useState({
    landmarks: 0,
    timestamp: 0,
  });

  const [squat_metrics] = useState({
    hip_angle: 0,
    knee_angle: 0,
    ankle_angle: 0,
    depth: 0,
    symmetry: 0,
    velocity: 0,
  });

  const { exercise } = route.params;

  return (
    <View style={styles.parentContainer}>
      <AppText variant="regular" style={styles.parentContainer}>
        User in Frame
      </AppText>
      <CameraPreview
        squat_session={squat_session}
        camera_status={camera_status}
        exercise={exercise}
      />
    </View>
  );
}

interface CameraPreviewProps {
  squat_session: SquatSession;
  camera_status: CameraStatus;
  exercise: RootStackParamList["CameraPose"]["exercise"];
}

function CameraPreview({
  squat_session,
  camera_status,
  exercise,
}: CameraPreviewProps) {
  return (
    <View style={styles.childContainer}>
      <AppText style={styles.childContainer}>User in Frame</AppText>
      <Text>{camera_status.landmark}</Text>
      <Text>{camera_status.angle}</Text>
      <Text>{exercise.bodyweight_squat}</Text>
    </View>
  );
}
