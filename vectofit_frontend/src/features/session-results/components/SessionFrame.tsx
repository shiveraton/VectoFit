import { type ReactNode } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";
import { styles as s } from "../theme/styles";

function recordedDay(value: string): string {
  const date = new Date(value);
  return date.toDateString() === new Date().toDateString()
    ? "TODAY"
    : date
        .toLocaleDateString(undefined, { month: "short", day: "numeric" })
        .toUpperCase();
}

export interface SessionFrameProps {
  children: ReactNode;
  controls?: ReactNode;
  recordedAt?: string;
  totalReps?: number;
  processing?: boolean;
  recordLabel?: string;
  modalOpen?: boolean;
  preview?: boolean;
  onBack: () => void;
  onRecord: () => void;
  onHistory: () => void;
}

export default function SessionFrame({
  children,
  controls,
  recordedAt,
  totalReps,
  processing = false,
  recordLabel = "Record next set",
  modalOpen = false,
  preview = false,
  onBack,
  onRecord,
  onHistory,
}: SessionFrameProps) {
  const insets = useSafeAreaInsets();
  const subtitle = [
    recordedAt ? recordedDay(recordedAt) : null,
    totalReps === undefined ? null : `${totalReps} REPS`,
    "FRONT VIEW",
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <SafeAreaView
      style={s.screen}
      edges={["top", "left", "right"]}
      accessibilityElementsHidden={modalOpen}
      importantForAccessibility={modalOpen ? "no-hide-descendants" : "auto"}
    >
      <View style={s.header}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Back to session history"
          onPress={onBack}
          style={({ pressed }) => [s.back, pressed && s.pressed]}
        >
          <Text style={s.backText} accessible={false}>
            ‹
          </Text>
        </Pressable>
        <View style={s.headerText}>
          <Text style={s.title} accessibilityRole="header">
            Session Results
          </Text>
          <Text style={s.caption}>{subtitle}</Text>
          {preview ? (
            <Text style={s.caption}>Development preview · Sample data</Text>
          ) : null}
        </View>
      </View>
      {controls}
      <ScrollView contentContainerStyle={s.content}>
        {children}
        <View
          style={[s.actions, { paddingBottom: Math.max(16, insets.bottom + 8) }]}
        >
          <Pressable
            accessibilityRole="button"
            disabled={processing}
            accessibilityState={{ disabled: processing, busy: processing }}
            onPress={processing ? undefined : onRecord}
            style={({ pressed }) => [
              s.button,
              s.primaryButton,
              processing && s.disabled,
              pressed && s.pressed,
            ]}
          >
            <Text style={s.buttonText}>
              {processing ? "Processing session..." : recordLabel}
            </Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            onPress={onHistory}
            style={({ pressed }) => [s.button, pressed && s.pressed]}
          >
            <Text style={[s.buttonText, s.secondaryText]}>
              View session history
            </Text>
          </Pressable>
        </View>
        </ScrollView>
    </SafeAreaView>
  );
}
