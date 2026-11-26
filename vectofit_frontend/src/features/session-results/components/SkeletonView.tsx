import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Line, Path } from "react-native-svg";
import type { Rep } from "../model/types";
import { angleAtTime, formatAngle, nearestFrame, projectSkeleton } from "../model/detail";
import { STATUS } from "../model/status";
import { tokens as t } from "../theme/tokens";
import { styles as s } from "../theme/styles";

export default function SkeletonView({ rep, mirrored, aspectRatio, timeMs }: { rep: Rep; mirrored: boolean | null; aspectRatio?: number | null; timeMs: number | null }) {
  const points = projectSkeleton(nearestFrame(rep, timeMs), mirrored, aspectRatio ?? 1);
  const left = `L ${formatAngle(angleAtTime(rep, "left", timeMs))}`;
  const right = `R ${formatAngle(angleAtTime(rep, "right", timeMs))}`;
  if (!points) return (
    <View style={s.section}>
      <Text style={s.caption}>Skeleton unavailable for this rep</Text>
      <View style={local.readouts}><Text style={s.body}>{left}</Text><Text style={s.body}>{right}</Text></View>
    </View>
  );
  const point = (name: keyof typeof points) => points[name].join(" ");
  return (
    <View style={local.skeleton} accessible accessibilityRole="image"
      accessibilityLabel={`Mirror view of rep ${rep.index}. ${left}, ${right}.`}
      importantForAccessibility="yes">
      <Svg width="100%" height="100%" viewBox="0 0 240 200" accessible={false}>
        <Line x1={120} x2={120} y1={8} y2={192} stroke={t.color.hairline} strokeDasharray="4 4" />
        <Circle cx={points.nose[0]} cy={points.nose[1]} r={9} fill="none" stroke={t.color.skeletonBody} strokeWidth={3} />
        <Line x1={points.nose[0]} y1={points.nose[1] + 9}
          x2={(points.lShoulder[0] + points.rShoulder[0]) / 2} y2={(points.lShoulder[1] + points.rShoulder[1]) / 2}
          stroke={t.color.skeletonBody} strokeWidth={3} />
        <Path d={`M${point("lShoulder")} L${point("rShoulder")} L${point("rHip")} L${point("lHip")} Z`}
          fill="none" stroke={t.color.skeletonBody} strokeWidth={3} strokeLinejoin="round" />
        <Line x1={points.lHip[0]} y1={points.lHip[1]} x2={points.rHip[0]} y2={points.rHip[1]}
          stroke={t.color.skeletonBody} strokeWidth={3} />
        {(["left", "right"] as const).map(side => (
          <Path key={side} d={side === "left"
            ? `M${point("lHip")} L${point("lKnee")} L${point("lAnkle")}`
            : `M${point("rHip")} L${point("rKnee")} L${point("rAnkle")}`}
            fill="none" stroke={STATUS[rep.kneeStatus[side]].fill} strokeWidth={4} strokeLinecap="round"
            strokeDasharray={STATUS[rep.kneeStatus[side]].dashed ? "5 4" : undefined} />
        ))}
      </Svg>
      <View style={StyleSheet.absoluteFill} pointerEvents="none" importantForAccessibility="no-hide-descendants">
        <Text style={[local.angle, { left: `${Math.max(0, Math.min(70, points.lKnee[0] / 240 * 100 - 22))}%`,
          top: `${Math.max(0, Math.min(85, points.lKnee[1] / 200 * 100))}%` }]}
          maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{left}</Text>
        <Text style={[local.angle, { left: `${Math.max(0, Math.min(70, points.rKnee[0] / 240 * 100 + 4))}%`,
          top: `${Math.max(0, Math.min(85, points.rKnee[1] / 200 * 100))}%` }]}
          maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{right}</Text>
      </View>
    </View>
  );
}

const local = StyleSheet.create({
  skeleton: { width: "100%", aspectRatio: 240 / 200, position: "relative" },
  angle: { position: "absolute", fontFamily: t.font.display, fontSize: 14, color: t.color.text },
  readouts: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", gap: 12 },
});
