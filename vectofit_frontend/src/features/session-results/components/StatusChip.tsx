import { StyleSheet, Text, View } from "react-native";
import { STATUS } from "../model/status";
import type { Status } from "../model/types";
import { tokens } from "../theme/tokens";
import StatusIcon from "./StatusIcon";

export default function StatusChip({ status, accessible = true }: { status: Status; accessible?: boolean }) {
  const presentation = STATUS[status];
  return (
    <View accessible={accessible} accessibilityRole="text" accessibilityLabel={presentation.label}
      style={[styles.chip, { borderColor: presentation.fill, borderStyle: presentation.dashed ? "dashed" : "solid" }]}>
      <StatusIcon name={presentation.icon} color={presentation.text} size={16} />
      <Text style={[styles.text, { color: presentation.text }]}
        maxFontSizeMultiplier={tokens.type.maxFontSizeMultiplier}>{presentation.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: { alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: 6,
    borderWidth: 1, borderRadius: tokens.size.pillRadius, backgroundColor: tokens.color.surfaceSubtle,
    paddingHorizontal: 10, paddingVertical: 6, maxWidth: "100%" },
  text: { fontFamily: tokens.font.text, fontSize: tokens.type.minimum, flexShrink: 1 },
});
