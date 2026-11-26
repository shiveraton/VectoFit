import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RootStackParamList } from "./types";

export function startSquatAssessment(navigation: Pick<NativeStackNavigationProp<RootStackParamList>, "navigate">) {
  navigation.navigate("CameraPose", { exercise: "bodyweight_squat", viewAngle: "frontal" });
}
