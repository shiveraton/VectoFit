import { useMemo, useRef, type ComponentRef } from "react";
import { PanResponder, StyleSheet, Text, View } from "react-native";
import type { Rep } from "../model/types";
import type { ChartScale } from "../model/detail";
import { timeFromPosition } from "../model/detail";
import { phaseAtTime } from "../model/selectors";
import { tokens as t } from "../theme/tokens";
import { styles as s } from "../theme/styles";

export default function PhaseScrubber({
  rep,
  timeMs,
  width,
  xScale,
  onChange,
}: {
  rep: Rep;
  timeMs: number | null;
  width: number;
  xScale: ChartScale | null;
  onChange: (timeMs: number) => void;
}) {
  const target = useRef<ComponentRef<typeof View>>(null);
  const origin = useRef<number | null>(null);
  const dragging = useRef(false);
  const current = useRef({ duration: rep.durationMs, width, onChange });
  current.current = { duration: rep.durationMs, width, onChange };
  const duration = rep.durationMs;
  const responder = useMemo(() => {
    const changeAt = (pageX: number) => {
      const latest = current.current;
      if (
        !dragging.current ||
        origin.current === null ||
        latest.duration === null
      )
        return;
      const time = timeFromPosition(
        pageX - origin.current,
        latest.width,
        latest.duration,
        t.size.chartGutter,
      );
      if (time !== null) latest.onChange(time);
    };
    const stop = () => {
      dragging.current = false;
      origin.current = null;
    };
    return PanResponder.create({
      onStartShouldSetPanResponder: () => false,
      // TODO(decision-16): Four dp of horizontal movement distinguishes drag from vertical scrolling.
      onMoveShouldSetPanResponder: (_, gesture) =>
        Math.abs(gesture.dx) > 4 && Math.abs(gesture.dx) > Math.abs(gesture.dy),
      onPanResponderGrant: (_, gesture) => {
        dragging.current = true;
        const pageX = gesture.moveX;
        target.current?.measureInWindow((x) => {
          if (dragging.current) {
            origin.current = x;
            changeAt(pageX);
          }
        });
      },
      onPanResponderMove: (_, gesture) => changeAt(gesture.moveX),
      onPanResponderRelease: stop,
      onPanResponderTerminate: stop,
    });
  }, []);
  // TODO(decision-16): Missing duration has no invented scrub range or playhead time.
  if (!xScale || duration === null)
    return <Text style={s.caption}>Timing unavailable for this rep</Text>;
  const phase = timeMs === null ? null : phaseAtTime(rep, timeMs);
  const position = timeMs === null ? null : xScale(timeMs);
  const ranges = rep.phases
    ? [0, rep.phases.descentEndMs, rep.phases.bottomEndMs, duration]
    : [0, duration];
  return (
    <View
      ref={target}
      {...responder.panHandlers}
      style={local.scrubber}
      testID="phase-scrubber"
      accessible
      accessibilityRole="adjustable"
      accessibilityLabel="Rep time"
      accessibilityValue={{
        min: 0,
        max: duration,
        now: timeMs ?? undefined,
        text:
          timeMs === null
            ? "Time not selected"
            : `${(timeMs / 1000).toFixed(1)}s${phase ? `, ${phase}` : ""}`,
      }}
      accessibilityActions={[{ name: "increment" }, { name: "decrement" }]}
      onAccessibilityAction={(event) => {
        const step =
          event.nativeEvent.actionName === "increment"
            ? 100
            : event.nativeEvent.actionName === "decrement"
              ? -100
              : 0;
        if (step)
          onChange(Math.max(0, Math.min(duration, (timeMs ?? 0) + step)));
      }}
    >
      {position !== null && timeMs !== null ? (
        <Text
          style={[
            s.caption,
            local.floating,
            { left: Math.max(0, Math.min(width - 56, position - 28)) },
          ]}
          maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}
        >
          {(timeMs / 1000).toFixed(1)}s
        </Text>
      ) : null}
      <View
        style={[
          local.track,
          { left: xScale(0), width: xScale(duration) - xScale(0) },
        ]}
      >
        {ranges.slice(0, -1).map((start, index) => (
          <View
            key={start}
            style={{
              width: xScale(ranges[index + 1]) - xScale(start),
              height: 12,
              backgroundColor:
                index === 1 ? t.color.neutralLine : t.color.surfaceSubtle,
            }}
          />
        ))}
      </View>
      {position !== null ? (
        <View
          pointerEvents="none"
          style={[local.thumb, { left: position - 12 }]}
        />
      ) : null}
      <View
        style={StyleSheet.absoluteFill}
        pointerEvents="none"
        importantForAccessibility="no-hide-descendants"
      >
        {[0, duration / 2, duration].map((time) => (
          <Text
            key={time}
            style={[s.caption, local.tick, { left: xScale(time) - 28 }]}
            maxFontSizeMultiplier={t.type.maxFontSizeMultiplier}
          >
            {(time / 1000).toFixed(1)}s
          </Text>
        ))}
      </View>
    </View>
  );
}

const local = StyleSheet.create({
  scrubber: { minHeight: 96, position: "relative" },
  floating: { position: "absolute", top: 0, width: 56, textAlign: "center" },
  track: {
    position: "absolute",
    top: 42,
    height: 12,
    flexDirection: "row",
    borderRadius: 6,
    overflow: "hidden",
  },
  thumb: {
    position: "absolute",
    top: 36,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: t.color.primary,
  },
  tick: { position: "absolute", top: 72, width: 56, textAlign: "center" },
});
