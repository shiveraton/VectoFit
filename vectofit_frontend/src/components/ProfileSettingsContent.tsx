import type { ReactNode } from "react";
import { ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import styles from "../styles/ProfileSettingsStyles";

export default function ProfileSettingsContent({ children }: { children: ReactNode }) {
  return (
    <SafeAreaView style={styles.safeArea} edges={["left", "right", "bottom"]}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        automaticallyAdjustKeyboardInsets
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}
