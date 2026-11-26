import Svg, { Circle, Path } from "react-native-svg";
import type { StatusIconName } from "../model/status";
import { tokens } from "../theme/tokens";

const paths: Record<StatusIconName, string> = {
  check: "M5 12l4 4L19 6",
  dash: "M5 12h14",
  arrowSW: "M18 6L6 18M6 8v10h10",
  eyeOff: "M3 3l18 18M10 5.2c.65-.13 1.32-.2 2-.2 6 0 10 7 10 7a19 19 0 0 1-3.2 3.8M6.1 6.1C3.5 8.2 2 12 2 12s4 7 10 7a11 11 0 0 0 5-1.3M10 10a3 3 0 0 0 4 4",
  warning: "M10.3 4.5L2.8 18a1.7 1.7 0 0 0 1.5 2.5h15.4a1.7 1.7 0 0 0 1.5-2.5L13.7 4.5a2 2 0 0 0-3.4 0M12 9v4",
};

export default function StatusIcon({ name, size = 24, color = tokens.color.text }: {
  name: StatusIconName;
  size?: number;
  color?: string;
}) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
      strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" accessible={false}>
      <Path d={paths[name]} />
      {name === "warning" ? <Circle cx={12} cy={17} r={0.5} fill={color} /> : null}
    </Svg>
  );
}
