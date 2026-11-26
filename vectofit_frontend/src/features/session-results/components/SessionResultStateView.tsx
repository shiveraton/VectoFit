import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import type { SessionResultState } from "../model/types";
import { selectErrorBody } from "../model/selectors";
import { STATUS } from "../model/status";
import { styles as s } from "../theme/styles";
import useReducedMotion from "../hooks/useReducedMotion";
import SessionResultView from "./SessionResultView";
import SessionFrame from "./SessionFrame";
import StatusIcon from "./StatusIcon";
import LoadingContent from "./LoadingContent";

export default function SessionResultStateView({ state, retry, retrying = false, controls, preview = false, onBack, onRecord, onHistory }: {
  state: SessionResultState;
  retry: () => Promise<void>;
  retrying?: boolean;
  controls?: ReactNode;
  preview?: boolean;
  onBack: () => void;
  onRecord: () => void;
  onHistory: () => void;
}) {
  const reducedMotion = useReducedMotion();
  if (state.status === "ready") return <SessionResultView key={state.data.sessionId} result={state.data}
    preview={preview} reducedMotion={reducedMotion} controls={controls} onBack={onBack} onRecord={onRecord} onHistory={onHistory} />;
  return (
    <SessionFrame preview={preview} controls={controls} processing={state.status === "loading" || retrying}
      recordLabel="Record a new set" onBack={onBack} onRecord={onRecord} onHistory={onHistory}>
      {state.status === "loading" ? <LoadingContent stage={state.stage} reducedMotion={reducedMotion} /> : (
        <View style={s.section}>
          <StatusIcon name="warning" color={STATUS.borderline.text} />
          <Text style={s.heading} accessibilityRole="header">We couldn't finish analyzing this session</Text>
          <Text style={s.body} accessibilityRole="alert">{selectErrorBody(state.error)}</Text>
          <Pressable accessibilityRole="button" disabled={retrying} accessibilityState={{ disabled: retrying, busy: retrying }}
            onPress={() => { if (!retrying) void retry(); }}
            style={({ pressed }) => [s.button, s.primaryButton, retrying && s.disabled, pressed && s.pressed]}>
            {retrying && !reducedMotion ? <ActivityIndicator color={s.buttonText.color} /> : null}
            <Text style={s.buttonText}>Try again</Text>
          </Pressable>
        </View>
      )}
    </SessionFrame>
  );
}
