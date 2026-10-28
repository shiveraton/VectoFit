import React from "react";
import { StyleSheet, View } from "react-native";
import Svg, { Line, Circle } from "react-native-svg";
import { Landmarks } from "../../screens/MorphologicalCalibrationScreen";

interface LandmarkOverlayProps {
  landmarks: Landmarks | null;
  isValid: boolean;
  frameWidth?: number;
  frameHeight?: number;
  viewportWidth: number;
  viewportHeight: number;
  mirrored?: boolean;
}

export const LandmarkOverlay: React.FC<LandmarkOverlayProps> = ({
  landmarks,
  isValid,
  viewportWidth,
  viewportHeight,
  frameWidth = 360,
  frameHeight = 360,
  mirrored = false,
}) => {
  if (!landmarks) return null;

  const vectorColor = isValid ? "#22C55E" : "#EF4444";
  const jointColor = isValid ? "#4ADE80" : "#F87171";

  const mapPt = (lm: { x_coordinate: number; y_coordinate: number }) => ({
    x: lm.x_coordinate * frameWidth,
    y: lm.y_coordinate * frameHeight,
  });

  const ls = mapPt(landmarks.left_shoulder);
  const rs = mapPt(landmarks.right_shoulder);
  const lh = mapPt(landmarks.left_hip);
  const rh = mapPt(landmarks.right_hip);
  const lk = mapPt(landmarks.left_knee);
  const rk = mapPt(landmarks.right_knee);
  const la = mapPt(landmarks.left_ankle);
  const ra = mapPt(landmarks.right_ankle);

  const boneConnections = [
    [ls, rs], // Shoulder girdle
    [lh, rh], // Pelvic girdle
    [ls, lh], // Left torso
    [rs, rh], // Right torso
    [lh, lk], // Left femur
    [lk, la], // Left tibia/fibula
    [rh, rk], // Right femur
    [rk, ra], // Right tibia/fibula
  ];

  const joints = [ls, rs, lh, rh, lk, rk, la, ra];

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg
        height="100%"
        width="100%"
        viewBox={`0 0 ${frameWidth} ${frameHeight}`}
      >
        {boneConnections.map(([p1, p2], idx) => (
          <Line
            key={`bone-${idx}`}
            x1={p1.x}
            y1={p1.y}
            x2={p2.x}
            y2={p2.y}
            stroke={vectorColor}
            strokeWidth="3"
            strokeLinecap="round"
          />
        ))}

        {joints.map((pt, idx) => (
          <Circle
            key={`joint-${idx}`}
            cx={pt.x}
            cy={pt.y}
            r="6"
            fill={jointColor}
            stroke="#FFFFFF"
            strokeWidth="1.5"
          />
        ))}
      </Svg>
    </View>
  );
};
