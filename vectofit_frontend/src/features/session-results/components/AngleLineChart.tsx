import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Line, Path } from "react-native-svg";
import type { Rep } from "../model/types";
import { angleAtTime, formatAngle, lineLabelPositions, seriesPath, type ChartScale } from "../model/detail";
import { yTicks } from "../model/selectors";
import { STATUS } from "../model/status";
import { tokens as t } from "../theme/tokens";
import { styles as s } from "../theme/styles";

export default function AngleLineChart({ rep, signedAngles = false, timeMs, width, xScale, yScale, yMax }: {
  rep: Rep; signedAngles?: boolean; timeMs: number | null; width: number; xScale: ChartScale | null; yScale: ChartScale; yMax: number;
}) {
  const { series, durationMs } = rep;
  // TODO(decision-16): Missing or invalid series stays unavailable rather than drawing a substitute curve.
  if (!series || !xScale || durationMs === null) return <Text style={s.caption}>Angle data unavailable for this rep</Text>;
  const plotY = (value: number) => t.size.chartHeight - yScale(value);
  const curves = (["left", "right"] as const).map(side => {
    const values = side === "left" ? series.leftDeg : series.rightDeg;
    const state = rep.kneeStatus[side];
    const path = seriesPath(series.tMs, values, xScale, plotY);
    const window = rep.offTrack?.[side];
    const highlight = window && (state === "deviated" || state === "borderline")
      ? seriesPath(series.tMs, values, xScale, plotY, window) : "";
    return { side, path, highlight, color: state === "aligned" ? STATUS.aligned.fill : t.color.neutralLine,
      offTrackColor: STATUS[state].fill, endY: plotY(values[values.length - 1]) };
  });
  if (curves.some(curve => !curve.path)) return <Text style={s.caption}>Angle data unavailable for this rep</Text>;
  const labels = lineLabelPositions(curves[0].endY, curves[1].endY, t.size.chartHeight);
  const endTime = series.tMs[series.tMs.length - 1];
  const peak = rep.peakAtMs !== null && rep.worstPeakDeg !== null
    ? { x: xScale(rep.peakAtMs), y: plotY(rep.worstPeakDeg) } : null;
  const offTrack = curves.filter(curve => curve.highlight);
  return (
    <View style={s.section}>
      <View style={local.chart} accessible accessibilityRole="image"
        accessibilityLabel={`Rep ${rep.index} inward knee angles. Left ${formatAngle(angleAtTime(rep, "left", timeMs))}, right ${formatAngle(angleAtTime(rep, "right", timeMs))}${timeMs === null ? "" : ` at ${(timeMs / 1000).toFixed(1)} seconds`}.`}
        testID="angle-line-chart">
        <View style={StyleSheet.absoluteFill} importantForAccessibility="no-hide-descendants">
          <Svg width={width} height={t.size.chartHeight} style={local.plot} accessible={false}>
            {yTicks(yMax, signedAngles).map(tick => <Line key={tick} x1={xScale(0)} x2={xScale(durationMs)}
              y1={plotY(tick)} y2={plotY(tick)} stroke={t.color.hairline} />)}
            {curves.map(curve => <Path key={curve.side} d={curve.path} fill="none"
              stroke={curve.color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />)}
            {offTrack.map(curve => <Path key={`off-${curve.side}`} d={curve.highlight} fill="none"
              stroke={curve.offTrackColor} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />)}
            {curves.map(curve => <Line key={`label-${curve.side}`} x1={xScale(endTime)} x2={xScale(durationMs) + 6}
              y1={curve.endY} y2={labels[curve.side]} stroke={curve.color} />)}
            {peak ? <Circle cx={peak.x} cy={peak.y} r={4} fill={t.color.primary} /> : null}
            {timeMs !== null ? <Line x1={xScale(timeMs)} x2={xScale(timeMs)} y1={0} y2={t.size.chartHeight}
              stroke={t.color.primary} strokeDasharray="4 4" testID="angle-cursor" /> : null}
          </Svg>
          {yTicks(yMax, signedAngles).map(tick => <Text key={tick} style={[s.caption, local.axis, { top: 20 + plotY(tick) - 9 }]}
            maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{tick}°</Text>)}
          {curves.map(curve => <Text key={curve.side} style={[local.label,
            { left: xScale(durationMs) + 8, top: 20 + labels[curve.side] - 10 }]}
            maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{curve.side === "left" ? "L" : "R"}</Text>)}
          {peak ? <Text style={[s.caption, local.peak, {
            left: Math.max(t.size.chartGutter, Math.min(width - t.size.chartGutter - 40, peak.x - 20)),
            top: Math.max(0, 20 + peak.y - 24),
          }]} maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{formatAngle(rep.worstPeakDeg)}</Text> : null}
        </View>
      </View>
      {offTrack.length ? <View style={local.key}>
        {offTrack.map(curve => <View key={curve.side} style={[local.swatch, { backgroundColor: curve.offTrackColor }]} />)}
        <Text style={s.caption}>Off-track</Text>
      </View> : null}
    </View>
  );
}

const local = StyleSheet.create({
  chart: { height: t.size.chartHeight + 40, position: "relative" },
  plot: { position: "absolute", top: 20, left: 0 },
  axis: { position: "absolute", left: 0 },
  label: { position: "absolute", color: t.color.text, fontFamily: t.font.display, fontSize: 14 },
  peak: { position: "absolute", width: 40, textAlign: "center" },
  key: { flexDirection: "row", alignItems: "center", gap: 6 },
  swatch: { width: 16, height: 4, borderRadius: 2 },
});
