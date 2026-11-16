import { Alert, Linking, TouchableOpacity, View } from "react-native";
import { AppText } from "../components/AppText";
import ProfileSettingsContent from "../components/ProfileSettingsContent";
import styles from "../styles/ProfileSettingsStyles";

export default function PrivacySecurityScreen() {
  const openSettings = async () => {
    try {
      await Linking.openSettings();
    } catch {
      Alert.alert("Unable to open settings", "Open your device settings and select VectoFit to review app permissions.");
    }
  };

  return (
    <ProfileSettingsContent>
      <View style={styles.section}>
        <AppText style={styles.heading} variant="semiBold" accessibilityRole="header">Assessment data</AppText>
        <AppText style={styles.body}>Recorded assessment videos are uploaded to the server for processing. Session results are available through your account in Insights.</AppText>
      </View>
      <View style={styles.section}>
        <AppText style={styles.heading} variant="semiBold" accessibilityRole="header">Device permissions</AppText>
        <AppText style={styles.body}>Camera access is used for recording. Microphone and speech recognition access are used when voice controls are enabled. Review or revoke permissions in your device settings.</AppText>
      </View>
      <TouchableOpacity style={styles.button} accessibilityRole="button" onPress={() => void openSettings()}>
        <AppText style={styles.buttonText} variant="semiBold">Open device settings</AppText>
      </TouchableOpacity>
      <View style={styles.section}>
        <AppText style={styles.heading} variant="semiBold" accessibilityRole="header">Signing out</AppText>
        <AppText style={styles.body}>VectoFit keeps your sign-in session on this device. Use Log Out on your Profile when using a shared device. Signing out does not delete your account or uploaded assessments.</AppText>
      </View>
    </ProfileSettingsContent>
  );
}
