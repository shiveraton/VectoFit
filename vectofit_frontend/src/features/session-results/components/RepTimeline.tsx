import { useRef, useState, type ComponentRef } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import type { Rep, SessionResult, Status } from "../model/types";
import { yTicks } from "../model/selectors";
import type { ChartScale } from "../model/detail";
import { STATUS } from "../model/status";
import { tokens as t } from "../theme/tokens";
import { styles as s } from "../theme/styles";
import StatusIcon from "./StatusIcon";
import StatusFill from "./StatusFill";
import useSelectionScroll from "../hooks/useSelectionScroll";

const chartHeight = t.size.chartHeight;
const statuses = Object.keys(STATUS) as Status[];

export default function RepTimeline({ result, selectedRep, yMax, yScale, onSelect, reducedMotion = true }: {
  result: SessionResult;
  selectedRep: Rep | null;
  yMax: number;
  yScale: ChartScale;
  onSelect: (rep: Rep) => void;
  reducedMotion?: boolean;
}) {
  const chart = useRef<ComponentRef<typeof ScrollView>>(null);
  const pills = useRef<ComponentRef<typeof ScrollView>>(null);
  const [width, setWidth] = useState(0);
  const selectedIndex = result.reps.findIndex(rep => rep.index === selectedRep?.index);
  const cellWidth = Math.max(t.size.touch, (width - 32) / Math.max(1, result.reps.length));
  const hasUnmeasured = result.reps.some(rep => rep.status === "unassessable" || rep.worstPeakDeg === null);

  const plotWidth = Math.max(0, width - 32);
  const target = selectedIndex < 0 || width <= 0 ? null : {
    chart: Math.min(Math.max(0, cellWidth * result.reps.length - plotWidth), Math.max(0, selectedIndex * cellWidth - (plotWidth - cellWidth) / 2)),
    pills: Math.min(Math.max(0, result.reps.length * (t.size.repWidth + 8) - 8 - width),
      Math.max(0, selectedIndex * (t.size.repWidth + 8) - (width - t.size.repWidth) / 2)),
  };
  const scrolling = useSelectionScroll(chart, pills, target, reducedMotion);

  return (
    <View style={s.section} onLayout={event => setWidth(event.nativeEvent.layout.width)}>
      {/* TODO(decision-14): Use the preview's plain-language section labels. */}
      <Text style={s.heading} accessibilityRole="header">Review your reps</Text>
      <View style={local.chart} accessible accessibilityRole="image"
        accessibilityLabel={result.reps.map(rep => `Rep ${rep.index}, ${STATUS[rep.status].label}, ${rep.worstPeakDeg === null ? "not measured" : `${rep.worstPeakDeg} degrees peak`}`).join(". ")}>
        <View style={local.axis} importantForAccessibility="no-hide-descendants">
          {yTicks(yMax, result.signedAngles).map(tick => <Text key={tick} style={[s.caption, local.tick, { bottom: yScale(tick) - 9 }]}
            maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{tick}°</Text>)}
        </View>
        <ScrollView ref={chart} horizontal showsHorizontalScrollIndicator={false} importantForAccessibility="no-hide-descendants"
          onScroll={scrolling.onChartScroll} scrollEventThrottle={16} onScrollBeginDrag={scrolling.onDragStart}>
          <View style={[local.plot, { width: cellWidth * result.reps.length }]}>
            {yTicks(yMax, result.signedAngles).map(tick => <View key={tick} pointerEvents="none" style={[local.gridLine, { bottom: yScale(tick) }]} />)}
            {result.reps.map(rep => {
              const selected = rep.index === selectedRep?.index;
              const peak = rep.worstPeakDeg;
              const measured = rep.status !== "unassessable" && peak !== null;
              const height = measured ? Math.abs(yScale(peak) - yScale(0)) : chartHeight * 0.15;
              return (
                <Pressable key={rep.index} accessible={false} testID={`rep-bar-${rep.index}`} onPress={() => onSelect(rep)}
                  style={({ pressed }) => [local.barTarget, { width: cellWidth }, pressed && s.pressed]}>
                  <View style={[local.bar, { height: Math.max(2, height), position: "absolute",
                    bottom: measured ? Math.min(yScale(peak), yScale(0)) : Math.max(0, yScale(0) - height),
                    borderColor: selected ? t.color.primary : "transparent", borderWidth: selected ? 2 : 0 }]}>
                    <View style={local.barInterior}><StatusFill status={measured ? rep.status : "unassessable"} /></View>
                  </View>
                </Pressable>
              );
            })}
          </View>
        </ScrollView>
      </View>
      <Text style={s.caption}>{result.signedAngles ? "Peak knee angle per rep (worse knee)" : "Peak inward angle per rep (worse knee)"}{hasUnmeasured ? " Hatched = not measured." : ""}</Text>
      <ScrollView ref={pills} horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={local.pills}
        onScroll={scrolling.onPillsScroll} scrollEventThrottle={16} onScrollBeginDrag={scrolling.onDragStart}>
        {result.reps.map(rep => {
          const selected = rep.index === selectedRep?.index;
          const presentation = STATUS[rep.status];
          return (
            <Pressable key={rep.index} accessibilityRole="button" accessibilityState={{ selected }}
              accessibilityLabel={`Rep ${rep.index}, ${presentation.label.toLowerCase()}, ${rep.worstPeakDeg === null ? "not measured" : `${rep.worstPeakDeg} degrees peak`}${selected ? ", selected" : ""}`}
              onPress={() => onSelect(rep)} testID={`rep-pill-${rep.index}`}
              style={({ pressed }) => [local.pill, {
                borderColor: selected ? t.color.primary : presentation.fill,
                borderStyle: presentation.dashed ? "dashed" : "solid",
                borderWidth: selected ? 2 : 1,
                backgroundColor: selected ? t.color.primaryDim : t.color.surface,
              }, pressed && s.pressed]}>
              <Text style={s.body} maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{rep.index}</Text>
              <StatusIcon name={presentation.icon} color={presentation.text} size={16} />
            </Pressable>
          );
        })}
      </ScrollView>
      <View style={local.legend}>
        {statuses.map(status => <View key={status} style={local.legendItem} accessible
          accessibilityLabel={`${STATUS[status].label}, ${result.summary.counts[status]} reps`}>
          <StatusIcon name={STATUS[status].icon} color={STATUS[status].text} size={16} />
          <Text style={s.caption}>{STATUS[status].label} · {result.summary.counts[status]}</Text>
        </View>)}
      </View>
    </View>
  );
}

const local = StyleSheet.create({
  chart: { flexDirection: "row", paddingVertical: 12 },
  axis: { width: 32, height: chartHeight },
  tick: { position: "absolute", left: 0 },
  plot: { height: chartHeight, flexDirection: "row", alignItems: "flex-end" },
  gridLine: { position: "absolute", left: 0, right: 0, height: 1, backgroundColor: t.color.hairline },
  barTarget: { height: chartHeight, alignItems: "center", justifyContent: "flex-end", paddingHorizontal: 6 },
  bar: { width: "100%", overflow: "hidden", borderRadius: 4 },
  barInterior: { width: "100%", flex: 1, position: "relative" },
  pills: { gap: 8, paddingVertical: 4 },
  pill: { width: t.size.repWidth, minHeight: t.size.repHeight, borderRadius: t.size.pillRadius,
    alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 8 },
  legend: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 4 },
});
