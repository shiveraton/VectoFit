import { useRef, type ComponentRef } from "react";
import { AccessibilityInfo, findNodeHandle, Modal, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import type { ExplainKind } from "./MetricGrid";
import { styles as s } from "../theme/styles";

const explanations: Record<ExplainKind, { title: string; body: string }> = {
  left: { title: "Left Knee", body: "This is how far your left knee moved toward the middle of your body at its worst point in this set. Your knee should stay in line with your foot." },
  right: { title: "Right Knee", body: "This is how far your right knee moved toward the middle of your body at its worst point in this set. Your knee should stay in line with your foot." },
  balance: { title: "L/R Balance", body: "This compares how far each knee moved inward. A bigger gap means one knee is drifting more than the other." },
  tracking: { title: "Tracking", body: "This shows how many reps the camera could see clearly. Reps where a knee left the frame can't be assessed." },
};

export default function ExplainSheet({ kind, signedAngles = false, onClose, onDismiss }: {
  kind: ExplainKind | null;
  signedAngles?: boolean;
  onClose: () => void;
  onDismiss: () => void;
}) {
  const insets = useSafeAreaInsets();
  const title = useRef<ComponentRef<typeof Text>>(null);
  const explanation = kind ? explanations[kind] : null;
  const body = signedAngles && (kind === "left" || kind === "right")
    ? "The largest recorded knee angle. Positive angles indicate inward movement; negative angles indicate outward movement."
    : signedAngles && kind === "balance" ? "This compares the magnitude of each knee's largest recorded angle, regardless of direction. A positive difference means the right knee's magnitude is larger."
      : explanation?.body;
  return (
    <Modal visible={kind !== null} transparent animationType="none" onRequestClose={onClose} onDismiss={onDismiss}
      onShow={() => { const node = findNodeHandle(title.current); if (typeof node === "number") AccessibilityInfo.setAccessibilityFocus(node); }}>
      <View style={s.modalBackdrop}>
        <View style={[s.sheet, { paddingBottom: Math.max(24, insets.bottom + 16), maxHeight: "85%" }]}
          accessibilityViewIsModal importantForAccessibility="yes">
          <ScrollView style={s.sheetScroll} contentContainerStyle={s.sheetContent}>
            <Text ref={title} style={s.heading} accessibilityRole="header">{explanation?.title}</Text>
            <Text style={s.body}>{body}</Text>
          </ScrollView>
          <Pressable accessibilityRole="button" accessibilityLabel="Close explanation" onPress={onClose}
            style={({ pressed }) => [s.button, pressed && s.pressed]}>
            {/* TODO(decision-14): Close is the default text-only explanation action. */}
            <Text style={[s.buttonText, s.secondaryText]}>Close</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}
