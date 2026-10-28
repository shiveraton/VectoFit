import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { MorphologicalData } from "../../screens/MorphologicalCalibrationScreen";

interface CalibrationResultProps {
  data: MorphologicalData;
  onContinue: () => void;
  onRetry: () => void;
}

export const CalibrationResult: React.FC<CalibrationResultProps> = ({
  data,
  onContinue,
  onRetry,
}) => {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Calibration Complete</Text>
      <View style={styles.row}>
        <Text style={styles.label}>Trunk Length:</Text>
        <Text style={styles.value}>{data.trunk.toFixed(1)} cm</Text>
      </View>
      <View style={styles.row}>
        <Text style={styles.label}>Left Lower Limb:</Text>
        <Text style={styles.value}>{data.left_lower_limb.toFixed(1)} cm</Text>
      </View>
      <View style={styles.row}>
        <Text style={styles.label}>Right Lower Limb:</Text>
        <Text style={styles.value}>{data.right_lower_limb.toFixed(1)} cm</Text>
      </View>

      <TouchableOpacity style={styles.primaryBtn} onPress={onContinue}>
        <Text style={styles.btnText}>Continue to Workout</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.secondaryBtn} onPress={onRetry}>
        <Text style={styles.secondaryBtnText}>Recalibrate</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#1E293B",
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: "#22C55E",
  },
  title: {
    color: "#22C55E",
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 12,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  label: { color: "#94A3B8", fontSize: 14 },
  value: { color: "#F8FAFC", fontSize: 14, fontWeight: "600" },
  primaryBtn: {
    backgroundColor: "#6366F1",
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: "center",
    marginTop: 12,
  },
  secondaryBtn: { alignItems: "center", marginTop: 8, paddingVertical: 6 },
  btnText: { color: "#FFF", fontWeight: "700" },
  secondaryBtnText: { color: "#94A3B8", fontSize: 13 },
});
