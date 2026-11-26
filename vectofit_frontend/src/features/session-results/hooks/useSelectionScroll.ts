import { useEffect, useRef, type ComponentRef, type RefObject } from "react";
import { Animated, type NativeScrollEvent, type NativeSyntheticEvent, type ScrollView } from "react-native";
import { tokens } from "../theme/tokens";

type ScrollRef = RefObject<ComponentRef<typeof ScrollView> | null>;

export default function useSelectionScroll(
  chart: ScrollRef, pills: ScrollRef, target: { chart: number; pills: number } | null, reducedMotion: boolean,
) {
  const position = useRef({ chart: 0, pills: 0 });
  const progress = useRef(new Animated.Value(0)).current;
  const running = useRef<Animated.CompositeAnimation | null>(null);
  useEffect(() => {
    if (!target) return;
    const destination = { ...target };
    const apply = (value: { chart: number; pills: number }) => {
      position.current = value;
      chart.current?.scrollTo({ x: value.chart, animated: false });
      pills.current?.scrollTo({ x: value.pills, animated: false });
    };
    const start = { ...position.current };
    if (reducedMotion || (start.chart === destination.chart && start.pills === destination.pills)) { apply(destination); return; }
    progress.setValue(0);
    const listener = progress.addListener(({ value }) => apply({
      chart: start.chart + (destination.chart - start.chart) * value,
      pills: start.pills + (destination.pills - start.pills) * value,
    }));
    const animation = Animated.timing(progress, { toValue: 1, duration: tokens.motion.selectionScrollMs, useNativeDriver: false });
    running.current = animation;
    animation.start();
    return () => { animation.stop(); progress.removeListener(listener); };
  }, [target?.chart, target?.pills, reducedMotion, chart, pills, progress]);
  return {
    onChartScroll: (event: NativeSyntheticEvent<NativeScrollEvent>) => { position.current.chart = event.nativeEvent.contentOffset.x; },
    onPillsScroll: (event: NativeSyntheticEvent<NativeScrollEvent>) => { position.current.pills = event.nativeEvent.contentOffset.x; },
    onDragStart: () => running.current?.stop(),
  };
}
