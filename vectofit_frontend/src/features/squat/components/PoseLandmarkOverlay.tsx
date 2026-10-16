import React from "react";
import { StyleSheet, View } from "react-native";
import Svg, { Circle, Line } from "react-native-svg";

import type { PoseLandmark } from "../hooks/useCameraPoseScreen";

interface PoseLandmarkOverlayProps {
  landmarks: PoseLandmark[];
  viewportWidth: number;
  viewportHeight: number;
  sourceFrameWidth: number;
  sourceFrameHeight: number;
  mirrored?: boolean;
}

interface Point {
  x: number;
  y: number;
}

const MIN_VISIBILITY = 0.45;

const CONNECTIONS: ReadonlyArray<readonly [number, number]> = [
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [27, 29],
  [29, 31],
  [24, 26],
  [26, 28],
  [28, 30],
  [30, 32],
];

const JOINTS = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32];

export default function PoseLandmarkOverlay({
  landmarks,
  viewportWidth,
  viewportHeight,
  sourceFrameWidth,
  sourceFrameHeight,
  mirrored = false,
}: PoseLandmarkOverlayProps) {
  if (landmarks.length !== 33 || viewportWidth <= 0 || viewportHeight <= 0) {
    return null;
  }

  const hasSourceSize = sourceFrameWidth > 0 && sourceFrameHeight > 0;

  const scale = hasSourceSize
    ? Math.max(
        viewportWidth / sourceFrameWidth,
        viewportHeight / sourceFrameHeight,
      )
    : 1;

  const renderedWidth = hasSourceSize
    ? sourceFrameWidth * scale
    : viewportWidth;

  const renderedHeight = hasSourceSize
    ? sourceFrameHeight * scale
    : viewportHeight;

  const cropX = (renderedWidth - viewportWidth) / 2;
  const cropY = (renderedHeight - viewportHeight) / 2;

  const points: Array<Point | null> = landmarks.map((landmark) => {
    if (
      !Number.isFinite(landmark.x_coordinate) ||
      !Number.isFinite(landmark.y_coordinate) ||
      !Number.isFinite(landmark.visibility) ||
      landmark.visibility < MIN_VISIBILITY
    ) {
      return null;
    }

    let x = landmark.x_coordinate * renderedWidth - cropX;

    const y = landmark.y_coordinate * renderedHeight - cropY;

    if (mirrored) {
      x = viewportWidth - x;
    }

    return { x, y };
  });

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg
        width={viewportWidth}
        height={viewportHeight}
        viewBox={`0 0 ${viewportWidth} ${viewportHeight}`}
        preserveAspectRatio="none"
      >
        {CONNECTIONS.map(([from, to], index) => {
          const start = points[from];
          const end = points[to];

          if (!start || !end) return null;

          return (
            <Line
              key={`bone-${index}`}
              x1={start.x}
              y1={start.y}
              x2={end.x}
              y2={end.y}
              stroke="#FDBA74"
              strokeWidth={3}
              strokeLinecap="round"
            />
          );
        })}

        {JOINTS.map((index) => {
          const point = points[index];

          if (!point) return null;

          return (
            <Circle
              key={`joint-${index}`}
              cx={point.x}
              cy={point.y}
              r={4}
              fill="#F97316"
              stroke="#FFFFFF"
              strokeWidth={1.2}
            />
          );
        })}
      </Svg>
    </View>
  );
}
