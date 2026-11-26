import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import type { PreviewScenario } from "../hooks/useSessionResultPreview";
import { styles as s } from "../theme/styles";
import { tokens as t } from "../theme/tokens";

// TODO(decision-17): These labels and scenarios are development controls, not assessment data.
const scenarios: { value: PreviewScenario; label: string }[] = [
  { value: "main", label: "Main" }, { value: "unassessable", label: "Unassessable" },
  { value: "all_aligned", label: "All aligned" }, { value: "zero_assessable", label: "No assessable reps" },
  { value: "limited", label: "Limited tracking" }, { value: "loading", label: "Loading" },
  { value: "tracking", label: "Tracking" }, { value: "counting", label: "Counting" }, { value: "checking", label: "Checking" },
  { value: "network_error", label: "Network error" }, { value: "processing_failed", label: "Processing failed" },
  { value: "unknown_error", label: "Unknown error" },
];

export default function PreviewControls({ selected, onSelect }: { selected: PreviewScenario; onSelect: (value: PreviewScenario) => void }) {
  if (!__DEV__) return null;
  return <View style={local.wrapper}>
    <Text style={s.caption}>Preview state</Text>
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={local.row}>
      {scenarios.map(scenario => <Pressable key={scenario.value} accessibilityRole="button"
        accessibilityState={{ selected: selected === scenario.value }} onPress={() => onSelect(scenario.value)}
        style={({ pressed }) => [local.option, selected === scenario.value && local.selected, pressed && s.pressed]}>
        <Text style={s.caption} maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{scenario.label}</Text>
      </Pressable>)}
    </ScrollView>
  </View>;
}

const local = StyleSheet.create({
  wrapper: { paddingHorizontal: t.size.screenPadding, paddingBottom: 12, gap: 4 },
  row: { gap: 8 },
  option: { minHeight: t.size.touch, justifyContent: "center", paddingHorizontal: 12, borderWidth: 1,
    borderColor: t.color.hairline, borderRadius: t.size.pillRadius },
  selected: { borderColor: t.color.primary, backgroundColor: t.color.primaryDim },
});
