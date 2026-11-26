import { useId } from "react";
import { StyleSheet, View } from "react-native";
import Svg, { Defs, Path, Pattern, Rect } from "react-native-svg";
import { STATUS } from "../model/status";
import type { Status } from "../model/types";
import { tokens } from "../theme/tokens";

export default function StatusFill({ status }: { status: Status }) {
  const id = useId().replace(/:/g, "");
  const presentation = STATUS[status];
  return (
    <View style={[StyleSheet.absoluteFill, { backgroundColor: presentation.fill,
      borderColor: presentation.fill, borderWidth: 1, borderStyle: presentation.dashed ? "dashed" : "solid" }]}
      pointerEvents="none" accessible={false} importantForAccessibility="no-hide-descendants">
      {presentation.dashed ? (
        <Svg width="100%" height="100%" accessible={false}>
          <Defs><Pattern id={id} width={8} height={8} patternUnits="userSpaceOnUse">
            <Path d="M-2 2L2-2M0 8L8 0M6 10L10 6" stroke={tokens.color.bg} strokeWidth={2} />
          </Pattern></Defs>
          <Rect width="100%" height="100%" fill={`url(#${id})`} />
        </Svg>
      ) : null}
    </View>
  );
}
