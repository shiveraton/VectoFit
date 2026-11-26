import { useState } from "react";
import { Text, View } from "react-native";
import type { Rep } from "../model/types";
import { selectInsight, selectUnassessableCopy } from "../model/selectors";
import { timeScale, type ChartScale } from "../model/detail";
import { STATUS } from "../model/status";
import { tokens as t } from "../theme/tokens";
import { styles as s } from "../theme/styles";
import StatusChip from "./StatusChip";
import SkeletonView from "./SkeletonView";
import PhaseScrubber from "./PhaseScrubber";
import AngleLineChart from "./AngleLineChart";

export default function RepDetailCard({ rep, mirrored, aspectRatio, signedAngles = false, timeMs, yMax, yScale, onScrub }: {
  rep: Rep; mirrored: boolean | null; aspectRatio?: number | null; signedAngles?: boolean; timeMs: number | null; yMax: number; yScale: ChartScale;
  onScrub: (timeMs: number) => void;
}) {
  const [width, setWidth] = useState(0);
  const xScale = timeScale(rep.durationMs, width, t.size.chartGutter);
  const unavailable = rep.status === "unassessable" ? selectUnassessableCopy(rep) : null;
  const insight = selectInsight(rep);
  return (
    <View style={s.card} testID="rep-detail-card">
      <View style={s.cardHeader} accessible accessibilityLiveRegion="polite"
        accessibilityLabel={`Rep ${rep.index}, ${STATUS[rep.status].label}`}>
        <Text style={s.heading}>Rep {rep.index}</Text>
        <StatusChip status={rep.status} accessible={false} />
      </View>
      {rep.modelEvidence ? <View style={s.section}>
        <Text style={s.caption}>Model knee alignment: {rep.modelEvidence.label === null ? "Unavailable" : rep.modelEvidence.label === "good" ? "Good" : "Bad"}
          {rep.modelEvidence.confidence === null ? "" : ` · Confidence ${Math.round(rep.modelEvidence.confidence * 100)}%`}</Text>
        {rep.modelEvidence.disagrees ? <Text style={s.body} accessibilityRole="alert">Results disagree. Review the model prediction and measured knee angles.</Text> : null}
      </View> : null}
      {unavailable ? <>
        <Text style={s.body}>{unavailable.title}</Text>
        <Text style={s.caption}>{unavailable.body}</Text>
      </> : <View style={s.section} onLayout={event => setWidth(event.nativeEvent.layout.width)} testID="rep-detail-layout">
        {timeMs !== null && rep.peakAtMs !== null && Math.abs(timeMs - rep.peakAtMs) <= 50
          ? <Text style={s.caption}>PEAK</Text> : null}
        <SkeletonView rep={rep} mirrored={mirrored} aspectRatio={aspectRatio} timeMs={timeMs} />
        <PhaseScrubber rep={rep} timeMs={timeMs} width={width} xScale={xScale} onChange={onScrub} />
        <AngleLineChart rep={rep} signedAngles={signedAngles} timeMs={timeMs} width={width} xScale={xScale} yScale={yScale} yMax={yMax} />
        {insight ? <Text style={s.body}>{insight}</Text> : null}
      </View>}
    </View>
  );
}
