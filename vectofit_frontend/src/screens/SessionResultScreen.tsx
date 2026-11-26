import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { InsightsStackParamList } from "../navigation/insightsTypes";
import SessionResultLive from "../features/session-results/SessionResultLive";
import SessionResultPreview from "../features/session-results/SessionResultPreview";

type Props = NativeStackScreenProps<InsightsStackParamList, "SessionResult">;

export default function SessionResultScreen(props: Props) {
  if (__DEV__ && props.route.params.previewFixture) return <SessionResultPreview {...props} />;
  return <SessionResultLive {...props} />;
}
