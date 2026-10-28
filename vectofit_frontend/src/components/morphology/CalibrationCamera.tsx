import React from "react";
import { View, StyleSheet } from "react-native";
import type { StyleProp, ViewStyle } from "react-native";
import { Camera } from "react-native-vision-camera";
import type {
  CameraDevice,
  CameraFrameOutput,
} from "react-native-vision-camera";

interface CalibrationCameraProps {
  device: CameraDevice;
  isActive: boolean;
  frameOutput?: CameraFrameOutput;
  containerStyle?: StyleProp<ViewStyle>;
  children?: React.ReactNode;
}

export const CalibrationCamera: React.FC<CalibrationCameraProps> = ({
  device,
  isActive,
  frameOutput,
  children,
}) => {
  return (
    <View style={styles.cameraContainer}>
      <Camera
        style={StyleSheet.absoluteFill}
        device={device}
        isActive={isActive}
        outputs={frameOutput ? [frameOutput] : undefined}
      />

      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  cameraContainer: {
    flex: 1,
    width: "100%",
    height: "100%",
    position: "relative",
    overflow: "hidden",
    backgroundColor: "#000000",
  },
});
