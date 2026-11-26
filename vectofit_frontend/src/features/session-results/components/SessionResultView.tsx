import { useRef, useState, type ComponentRef, type ReactNode } from "react";
import { AccessibilityInfo, findNodeHandle, Platform, Text, View } from "react-native";
import type { Rep, SessionResult } from "../model/types";
import { scale, selectComparison, selectDefaultRep, selectFocusCues, selectTier, selectTracking, yMaxOf } from "../model/selectors";
import { STATUS } from "../model/status";
import { tokens as t } from "../theme/tokens";
import { styles as s } from "../theme/styles";
import useCountUp from "../hooks/useCountUp";
import SessionFrame from "./SessionFrame";
import StatusIcon from "./StatusIcon";
import StatusFill from "./StatusFill";
import MetricGrid, { type ExplainKind } from "./MetricGrid";
import ExplainSheet from "./ExplainSheet";
import RepTimeline from "./RepTimeline";
import RepDetailCard from "./RepDetailCard";

export interface SessionResultViewProps {
  result: SessionResult;
  controls?: ReactNode;
  reducedMotion?: boolean;
  preview?: boolean;
  onBack: () => void;
  onRecord: () => void;
  onHistory: () => void;
}

function AlignedCount({ aligned, total, reducedMotion }: { aligned: number; total: number; reducedMotion: boolean }) {
  const count = useCountUp(aligned, reducedMotion);
  return <Text style={s.count} maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}
    accessibilityLabel={`${aligned} of ${total} reps aligned`}>
    {count}<Text style={s.countSuffix}>/{total} Reps</Text>
  </Text>;
}

export default function SessionResultView({ result, controls, preview = true, reducedMotion = true, onBack, onRecord, onHistory }: SessionResultViewProps) {
  const [selection, setSelection] = useState(() => {
    const rep = selectDefaultRep(result);
    return { rep, playheadMs: rep?.peakAtMs ?? null };
  });
  const [explanation, setExplanation] = useState<ExplainKind | null>(null);
  const returnFocus = useRef<ComponentRef<typeof View> | null>(null);
  const tier = selectTier(result);
  const tracking = selectTracking(result);
  const comparison = selectComparison(result);
  const cues = selectFocusCues(result);
  const yMax = yMaxOf(result.reps.map(rep => rep.worstPeakDeg));
  const yScale = scale(result.signedAngles ? -yMax : 0, yMax, 0, t.size.chartHeight);
  const selected = selection.rep;
  const restoreFocus = () => {
    const node = findNodeHandle(returnFocus.current);
    if (typeof node === "number") AccessibilityInfo.setAccessibilityFocus(node);
  };
  const closeExplanation = () => {
    setExplanation(null);
    if (Platform.OS === "android") requestAnimationFrame(restoreFocus);
  };
  const selectRep = (rep: Rep) => setSelection({ rep, playheadMs: rep.peakAtMs });

  return <>
    <SessionFrame preview={preview} controls={controls} recordedAt={result.recordedAt} totalReps={result.summary.totalReps}
      modalOpen={explanation !== null} onBack={onBack} onRecord={onRecord} onHistory={onHistory}>
      {tier.kind === "empty" ? <View style={s.hero}>
        <Text style={s.headline} accessibilityRole="header">We couldn't assess any reps</Text>
        <Text style={s.body}>Keep both knees in the frame and try again.</Text>
      </View> : <>
        {result.signedAngles ? <Text style={s.caption}>Measured knee alignment · Positive angles: inward. Negative angles: outward.</Text> : null}
        {result.presentation?.modelDisagreement ? <View style={s.warning} accessibilityRole="alert">
          <Text style={s.body}>Some model predictions differ from the measured knee angles. Review the affected reps.</Text>
        </View> : null}
        {tracking.limited ? <View style={s.warning} accessibilityRole="alert" accessibilityLiveRegion="polite">
          <StatusIcon name="warning" color={STATUS.borderline.text} />
          <Text style={s.body}>Tracking was weak in this set. Results may be less reliable.</Text>
          <Text style={s.caption}>{tracking.caption}</Text>
        </View> : null}
        <View style={s.hero}>
          <View style={s.tier}>
            <StatusIcon name={tier.kind === "needs_work" ? "warning" : "check"}
              color={tier.kind === "needs_work" ? STATUS.borderline.text : STATUS.aligned.text} size={20} />
            <Text style={[s.body, { color: tier.kind === "needs_work" ? STATUS.borderline.text : STATUS.aligned.text }]}
              maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{tier.label}</Text>
          </View>
          <AlignedCount aligned={result.summary.counts.aligned} total={result.summary.totalReps} reducedMotion={reducedMotion} />
          <Text style={s.headline} maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}>{tier.headline}</Text>
          {comparison ? <Text style={[s.caption, s.comparison]}>{comparison}</Text> : null}
          <View style={s.segments} accessible={false} importantForAccessibility="no-hide-descendants">
            {result.reps.map(rep => <View key={rep.index} style={s.segment}><StatusFill status={rep.status} /></View>)}
          </View>
        </View>
        <MetricGrid result={result} yMax={yMax} onExplain={(kind, target) => {
          returnFocus.current = target;
          setExplanation(kind);
        }} />
        <RepTimeline result={result} selectedRep={selected} yMax={yMax} yScale={yScale} onSelect={selectRep} reducedMotion={reducedMotion} />
        {selected ? <RepDetailCard rep={selected} mirrored={result.capture.mirrored} aspectRatio={result.capture.aspectRatio}
          signedAngles={result.signedAngles} timeMs={selection.playheadMs}
          yMax={yMax} yScale={yScale} onScrub={timeMs => setSelection(current => ({ ...current, playheadMs: timeMs }))} /> : null}
        {cues.length ? <View style={s.section}>
          <Text style={s.heading} accessibilityRole="header">Next set</Text>
          {cues.map(cue => <Text key={cue} style={s.body}>{cue}</Text>)}
        </View> : null}
      </>}
      <Text style={[s.caption, s.footer]}>Movement-quality estimate from camera analysis. Not medical advice.</Text>
    </SessionFrame>
    <ExplainSheet signedAngles={result.signedAngles} kind={explanation} onClose={closeExplanation} onDismiss={restoreFocus} />
  </>;
}
