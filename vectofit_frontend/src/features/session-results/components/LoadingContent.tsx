import { useEffect, useRef, useState } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import type { ProcessingStage } from "../model/types";
import { tokens as t } from "../theme/tokens";
import { styles as s } from "../theme/styles";

const steps: { stage: ProcessingStage; label: string }[] = [
  { stage: "tracking", label: "Tracking your body" },
  { stage: "counting", label: "Counting reps" },
  { stage: "checking", label: "Checking knee alignment" },
];

export default function LoadingContent({ stage, reducedMotion }: { stage?: ProcessingStage; reducedMotion: boolean }) {
  const progress = useRef(new Animated.Value(0)).current;
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (reducedMotion) return;
    progress.setValue(0);
    // TODO(decision-17): Loading shimmer uses a 1.2s indeterminate cycle, never assessment progress.
    const animation = Animated.loop(Animated.timing(progress, { toValue: 1, duration: t.motion.loadingMs, useNativeDriver: true }));
    animation.start();
    return () => animation.stop();
  }, [reducedMotion, progress]);
  const opacity = reducedMotion ? 1 : progress.interpolate({ inputRange: [0, 0.5, 1], outputRange: [0.35, 0.8, 0.35] });
  return (
    <View style={s.section}>
      <View accessibilityLiveRegion="polite" accessible accessibilityLabel={stage
        ? steps.find(step => step.stage === stage)?.label : "Analyzing your reps..."}>
        {stage ? steps.map(step => <Text key={step.stage} style={step.stage === stage ? s.body : s.caption}>{step.label}</Text>)
          : <Text style={s.body}>Analyzing your reps...</Text>}
      </View>
      <View style={local.progress} accessible accessibilityRole="progressbar" accessibilityLabel="Analyzing your reps"
        onLayout={event => setWidth(event.nativeEvent.layout.width)}>
        <Animated.View style={[local.indicator, !reducedMotion && { transform: [{ translateX: progress.interpolate({
          inputRange: [0, 1], outputRange: [-64, width],
        }) }] }]} />
      </View>
      <Animated.View style={[local.placeholders, { opacity }]} accessible={false} importantForAccessibility="no-hide-descendants">
        <View style={local.hero}>
          <View style={[local.block, { width: "40%", height: 28 }]} />
          <View style={[local.block, { width: "65%", height: 64 }]} />
          <View style={[local.block, { width: "100%", height: 48 }]} />
        </View>
        <View style={s.grid}>{[0, 1, 2, 3].map(index => <View key={index} style={[s.tile, index % 2 === 0 && s.tileLeft, { gap: 12 }]}>
          <View style={[local.block, { width: "70%", height: 20 }]} />
          <View style={[local.block, { width: "60%", height: 36 }]} />
          <View style={[local.block, { width: "100%", height: 32 }]} />
        </View>)}</View>
        <View style={[local.block, { height: t.size.chartHeight }]} />
        <View style={[local.block, { height: t.size.repHeight }]} />
      </Animated.View>
    </View>
  );
}

const local = StyleSheet.create({
  progress: { height: 4, backgroundColor: t.color.surfaceSubtle, overflow: "hidden", borderRadius: 2 },
  indicator: { width: 64, height: 4, backgroundColor: t.color.primary },
  placeholders: { gap: 24 },
  hero: { alignItems: "center", gap: 12 },
  block: { backgroundColor: t.color.surfaceSubtle, borderRadius: 8 },
});
