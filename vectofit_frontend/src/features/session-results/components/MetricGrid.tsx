import { useRef, type ComponentRef } from "react";
import { Pressable, Text, View } from "react-native";
import type { SessionResult } from "../model/types";
import { balanceFillPct, selectBalanceCaption, selectTracking } from "../model/selectors";
import { STATUS } from "../model/status";
import { tokens } from "../theme/tokens";
import { styles as s } from "../theme/styles";
import StatusChip from "./StatusChip";

export type ExplainKind = "left" | "right" | "balance" | "tracking";

export default function MetricGrid({ result, yMax, onExplain }: {
  result: SessionResult;
  yMax: number;
  onExplain: (kind: ExplainKind, target: ComponentRef<typeof View> | null) => void;
}) {
  const refs = useRef<Partial<Record<ExplainKind, ComponentRef<typeof View> | null>>>({});
  const tracking = selectTracking(result);
  const balance = result.summary.balanceDeg;
  const fill = balanceFillPct(balance, yMax);
  const balanceCaption = result.signedAngles && balance !== null ? (balance === 0 ? "Both knees even"
    : `${balance > 0 ? "Right" : "Left"} knee deviation is ${Math.abs(balance)}° larger`) : selectBalanceCaption(balance);
  return (
    <View style={s.grid}>
      {(["left", "right"] as const).map(side => {
        const knee = result.summary[side];
        const label = side === "left" ? "Left Knee" : "Right Knee";
        const value = knee.worstPeakDeg === null ? "—" : `${knee.worstPeakDeg}°`;
        return (
          <Pressable key={side} ref={node => { refs.current[side] = node; }} accessibilityRole="button"
            accessibilityLabel={`${label}, ${value}, ${STATUS[knee.status].label}, opens explanation`}
            onPress={() => onExplain(side, refs.current[side] ?? null)}
            style={({ pressed }) => [s.tile, side === "left" && s.tileLeft, pressed && s.pressed]}>
            <Text style={s.body}>{label}</Text>
            <StatusChip status={knee.status} accessible={false} />
            <Text style={s.value} maxFontSizeMultiplier={tokens.type.maxFontSizeMultiplier}>{value}</Text>
            <Text style={s.caption}>{result.signedAngles ? "Peak knee angle, worst rep" : "Peak inward angle, worst rep"}</Text>
          </Pressable>
        );
      })}
      <Pressable ref={node => { refs.current.balance = node; }} accessibilityRole="button"
        accessibilityLabel={`L/R Balance, ${balanceCaption ?? "not measured"}, opens explanation`}
        onPress={() => onExplain("balance", refs.current.balance ?? null)}
        style={({ pressed }) => [s.tile, s.tileLeft, pressed && s.pressed]}>
        <Text style={s.body}>L/R Balance</Text>
        <View style={s.balanceTrack} accessible={false}>
          {fill !== null && balance !== null ? <View style={[s.balanceFill, {
            width: `${fill}%`, left: `${balance < 0 ? 50 - fill : 50}%`,
          }]} /> : null}
          <View style={s.balanceZero} />
        </View>
        <Text style={s.caption}>{balanceCaption ?? "—"}</Text>
      </Pressable>
      <Pressable ref={node => { refs.current.tracking = node; }} accessibilityRole="button"
        accessibilityLabel={`Tracking, ${tracking.label}, ${tracking.caption}, opens explanation`}
        onPress={() => onExplain("tracking", refs.current.tracking ?? null)}
        style={({ pressed }) => [s.tile, pressed && s.pressed]}>
        <Text style={s.body}>Tracking</Text>
        <Text style={s.value} maxFontSizeMultiplier={tokens.type.maxFontSizeMultiplier}>{tracking.label}</Text>
        <Text style={s.caption}>{tracking.caption}</Text>
      </Pressable>
    </View>
  );
}
