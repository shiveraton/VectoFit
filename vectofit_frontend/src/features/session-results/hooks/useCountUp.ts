import { useEffect, useRef, useState } from "react";
import { Animated } from "react-native";
import { tokens } from "../theme/tokens";

export default function useCountUp(target: number, reducedMotion: boolean): number {
  const progress = useRef(new Animated.Value(0)).current;
  const [count, setCount] = useState(reducedMotion ? target : 0);
  const previous = useRef({ target, reducedMotion });
  useEffect(() => {
    // TODO(decision-17): Do not roll a displayed final count backward when the device preference arrives.
    const alreadyShown = previous.current.reducedMotion && previous.current.target === target;
    previous.current = { target, reducedMotion };
    if (reducedMotion || target === 0 || alreadyShown) { setCount(target); return; }
    progress.setValue(0);
    setCount(0);
    const listener = progress.addListener(({ value }) => setCount(Math.round(value)));
    const animation = Animated.timing(progress, { toValue: target, duration: tokens.motion.countUpMs, useNativeDriver: false });
    animation.start();
    return () => { animation.stop(); progress.removeListener(listener); };
  }, [target, reducedMotion, progress]);
  return reducedMotion ? target : count;
}
