import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack";
import type { InsightsStackParamList } from "../../navigation/insightsTypes";
import type { RootStackParamList } from "../../navigation/types";
import { startSquatAssessment } from "../../navigation/startSquatAssessment";
import useSessionResult from "./hooks/useSessionResult";
import SessionResultStateView from "./components/SessionResultStateView";

export default function SessionResultLive({ route, navigation }: NativeStackScreenProps<InsightsStackParamList, "SessionResult">) {
  const result = useSessionResult(route.params.sessionId);
  return <SessionResultStateView {...result} onBack={() => navigation.popTo("SessionHistory")}
    onHistory={() => navigation.popTo("SessionHistory")} onRecord={() => {
      const root = navigation.getParent()?.getParent<NativeStackNavigationProp<RootStackParamList>>();
      if (root) startSquatAssessment(root);
    }} />;
}
