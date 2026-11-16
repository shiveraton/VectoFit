import { View } from "react-native";
import { AppText } from "../components/AppText";
import ProfileSettingsContent from "../components/ProfileSettingsContent";
import styles from "../styles/ProfileSettingsStyles";

const topics = [
  {
    title: "Record an assessment",
    body: "Start a squat assessment from Home. Follow the camera guidance, keep your full body visible, and record from the front for knee-alignment assessment.",
  },
  {
    title: "Camera or voice controls unavailable",
    body: "Check VectoFit's camera and microphone permissions in your device settings. Voice controls also need speech recognition access. You can use the on-screen recording controls without voice commands.",
  },
  {
    title: "Results or uploads are delayed",
    body: "Check your internet connection and open Insights to check whether your session was saved before recording again. A failed or unavailable assessment is not a Good Form result.",
  },
  {
    title: "Measurements and units",
    body: "Update height and weight in Physical Information on Home. Enter height in centimetres and weight in kilograms. Knee angles are displayed in degrees.",
  },
  {
    title: "Account and data support",
    body: "In-app support messaging, password recovery, and account deletion are not available in this version. Account access and data requests require administrator assistance.",
  },
];

export default function HelpSupportScreen() {
  return (
    <ProfileSettingsContent>
      {topics.map(topic => (
        <View key={topic.title} style={styles.section}>
          <AppText style={styles.heading} variant="semiBold" accessibilityRole="header">{topic.title}</AppText>
          <AppText style={styles.body}>{topic.body}</AppText>
        </View>
      ))}
    </ProfileSettingsContent>
  );
}
