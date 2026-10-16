import React from "react";
import { View, Text, StyleSheet } from "react-native";

interface CalibrationGuideProps {
  feedback: string;
  isHolding: boolean;
}

export const CalibrationGuide: React.FC<CalibrationGuideProps> = ({
  feedback,
  isHolding,
}) => {
  return (
    <View style={styles.guideContainer} pointerEvents="none">
      <View
        style={[styles.alignmentBox, isHolding && styles.alignmentBoxActive]}
      />
      <View style={styles.feedbackBanner}>
        <Text style={styles.feedbackText}>{feedback}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  guideContainer: {
    ...StyleSheet.absoluteFill,
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 16,
  },
  alignmentBox: {
    width: "80%",
    height: "75%",
    borderWidth: 2,
    borderColor: "rgba(99, 102, 241, 0.6)",
    borderRadius: 16,
    borderStyle: "dashed",
  },
  alignmentBoxActive: {
    borderColor: "#22C55E",
  },
  feedbackBanner: {
    backgroundColor: "rgba(15, 23, 42, 0.85)",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  feedbackText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
});
