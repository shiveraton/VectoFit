import React from "react";
import { View, StyleSheet } from "react-native";

interface CalibrationProgressProps {
  progress: number;
}

export const CalibrationProgress: React.FC<CalibrationProgressProps> = ({
  progress,
}) => {
  return (
    <View style={styles.track}>
      <View
        style={[styles.bar, { width: `${Math.min(progress * 100, 100)}%` }]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  track: {
    height: 6,
    width: "100%",
    backgroundColor: "#334155",
    borderRadius: 3,
    marginTop: 8,
    overflow: "hidden",
  },
  bar: {
    height: "100%",
    backgroundColor: "#22C55E",
  },
});
