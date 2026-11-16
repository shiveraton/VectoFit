import { useState } from "react";
import { ActivityIndicator, Alert, TextInput, TouchableOpacity, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { AppText } from "../components/AppText";
import ProfileSettingsContent from "../components/ProfileSettingsContent";
import { getCurrentAccount, updateCurrentAccount, type AccountDetails } from "../features/profile/services/accountService";
import type { RootStackParamList } from "../navigation/types";
import useAuthStore from "../stores/useAuthStore";
import styles from "../styles/ProfileSettingsStyles";
import { COLORS } from "../styles/designTokens";

type AccountChanges = Pick<AccountDetails, "username" | "email">;
type AccountErrors = { username?: string[]; email?: string[]; detail?: string };

function ProfileEditor({ account }: { account: AccountDetails }) {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const sessionToken = useAuthStore(state => state.token);
  const [username, setUsername] = useState(account.username);
  const [email, setEmail] = useState(account.email);
  const save = useMutation<AccountDetails, AxiosError<AccountErrors>, AccountChanges>({
    mutationFn: changes => updateCurrentAccount(account.id, changes),
    onSuccess: updated => {
      if (useAuthStore.getState().token !== sessionToken) return;
      useAuthStore.getState().setUser({ id: String(updated.id), name: updated.username, email: updated.email });
      navigation.goBack();
      Alert.alert("Profile updated", "Your account details have been saved.");
    },
  });
  const errors = save.error?.response?.data;
  const unchanged = username.trim() === account.username && email.trim() === account.email;
  const disabled = save.isPending || unchanged || !username.trim();

  return (
    <>
      <View style={styles.field}>
        <AppText nativeID="profile-username-label" style={styles.label} variant="semiBold">Username</AppText>
        <TextInput
          style={styles.input}
          accessibilityLabel="Username"
          accessibilityLabelledBy="profile-username-label"
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="username"
          maxLength={150}
          value={username}
          editable={!save.isPending}
          onChangeText={value => { setUsername(value); save.reset(); }}
        />
        {errors?.username && <AppText style={styles.error}>{errors.username.join(" ")}</AppText>}
      </View>
      <View style={styles.field}>
        <AppText nativeID="profile-email-label" style={styles.label} variant="semiBold">Email (optional)</AppText>
        <TextInput
          style={styles.input}
          accessibilityLabel="Email, optional"
          accessibilityLabelledBy="profile-email-label"
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="email"
          maxLength={254}
          value={email}
          editable={!save.isPending}
          onChangeText={value => { setEmail(value); save.reset(); }}
        />
        {errors?.email && <AppText style={styles.error}>{errors.email.join(" ")}</AppText>}
      </View>
      {save.isError && (
        <AppText style={styles.error} accessibilityRole="alert" accessibilityLiveRegion="polite">
          {errors?.username || errors?.email ? "Check the fields above." : errors?.detail || "Unable to save your profile. Check your connection and try again."}
        </AppText>
      )}
      <TouchableOpacity
        style={[styles.button, disabled && styles.disabled]}
        accessibilityRole="button"
        accessibilityState={{ disabled, busy: save.isPending }}
        disabled={disabled}
        onPress={() => save.mutate({ username: username.trim(), email: email.trim() })}
      >
        <AppText style={styles.buttonText} variant="semiBold">{save.isPending ? "Saving…" : "Save changes"}</AppText>
      </TouchableOpacity>
      <AppText style={styles.body}>Height and weight are managed under Physical Information on the Home screen, in centimetres and kilograms.</AppText>
    </>
  );
}

export default function EditProfileScreen() {
  const userId = useAuthStore(state => state.user?.id);
  const query = useQuery({
    queryKey: ["profile-account", userId],
    queryFn: ({ signal }) => getCurrentAccount(signal),
    staleTime: 0,
    gcTime: 0,
    retry: false,
  });

  return (
    <ProfileSettingsContent>
      {query.isPending ? (
        <ActivityIndicator color={COLORS.primaryOrange} accessibilityLabel="Loading profile" />
      ) : query.isError ? (
        <>
          <AppText style={styles.error} accessibilityRole="alert">Unable to load your profile. Check your connection and try again.</AppText>
          <TouchableOpacity style={styles.button} accessibilityRole="button" onPress={() => void query.refetch()}>
            <AppText style={styles.buttonText} variant="semiBold">Retry</AppText>
          </TouchableOpacity>
        </>
      ) : <ProfileEditor key={query.data.id} account={query.data} />}
    </ProfileSettingsContent>
  );
}
