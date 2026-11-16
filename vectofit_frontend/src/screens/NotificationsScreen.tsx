import { TouchableOpacity, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { AppText } from "../components/AppText";
import ProfileSettingsContent from "../components/ProfileSettingsContent";
import type { RootStackParamList } from "../navigation/types";
import styles from "../styles/ProfileSettingsStyles";

export default function NotificationsScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  return (
    <ProfileSettingsContent>
      <View style={styles.section}>
        <AppText style={styles.heading} variant="semiBold" accessibilityRole="header">Assessment updates</AppText>
        <AppText style={styles.body}>VectoFit does not currently send push notifications or scheduled reminders. Open Insights to check your saved sessions and assessment results.</AppText>
      </View>
      <TouchableOpacity
        style={styles.button}
        accessibilityRole="button"
        onPress={() => navigation.popTo("MainTabs", { screen: "Insights", params: { screen: "SessionHistory" } })}
      >
        <AppText style={styles.buttonText} variant="semiBold">Open Insights</AppText>
      </TouchableOpacity>
    </ProfileSettingsContent>
  );
}
