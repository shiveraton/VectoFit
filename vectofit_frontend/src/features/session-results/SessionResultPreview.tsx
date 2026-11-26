import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import type { InsightsStackParamList } from "../../navigation/insightsTypes";
import type { RootStackParamList } from "../../navigation/types";
import useSessionResultPreview from "./hooks/useSessionResultPreview";
import SessionResultStateView from "./components/SessionResultStateView";
import PreviewControls from "./components/PreviewControls";

type Props = NativeStackScreenProps<InsightsStackParamList, "SessionResult">;

export default function SessionResultPreview({ route, navigation }: Props) {
  const fixture = route.params.previewFixture ?? "main";
  const preview = useSessionResultPreview(fixture);
  if (!preview.state) return null;
  return (
    <SessionResultStateView preview state={preview.state} retry={preview.retry} retrying={preview.retrying}
      controls={<PreviewControls selected={preview.scenario} onSelect={preview.selectScenario} />}
      onBack={() => navigation.popTo("SessionHistory")}
      onHistory={() => navigation.popTo("SessionHistory")}
      // TODO(decision-15): Home has no shared gate yet. Return there rather than bypassing setup.
      onRecord={() => navigation.getParent<BottomTabNavigationProp<RootStackParamList>>()?.navigate("Home")}
    />
  );
}
