import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../navigation/types";
import authStore from "../stores/authStore";
import { authStyles as styles } from "../styles/RegisterScreenStyles";

type RegisterProps = NativeStackScreenProps<RootStackParamList, "Register">;

export default function RegisterScreen({ navigation }: RegisterProps) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const register = authStore((state) => state.register);

  const handleRegister = async () => {
    const trimmedIdentifier = identifier.trim();

    if (!trimmedIdentifier || !password) {
      Alert.alert("Error", "Please fill in all fields.");
      return;
    }

    if (password.length < 6) {
      Alert.alert("Error", "Password must be at least 6 characters long.");
      return;
    }

    const isEmail = trimmedIdentifier.includes("@");

    const rawUsername = isEmail
      ? trimmedIdentifier.split("@")[0]
      : trimmedIdentifier;
    const sanitizedUsername = rawUsername.replace(/[^a-zA-Z0-9_]/g, "_");

    const registrationData = {
      email: isEmail
        ? trimmedIdentifier
        : `${sanitizedUsername.toLowerCase()}@vectofit.app`,
      username: sanitizedUsername,
      password: password,
      confirm_password: password,
    };

    try {
      setLoading(true);
      await register(registrationData);
      Alert.alert("Success", "Account created successfully!");
      navigation.navigate("Login");
    } catch (error: any) {
      console.error("Registration Error:", error);

      const apiMessage =
        error?.response?.data?.message ||
        error?.response?.data?.error ||
        (Array.isArray(error?.response?.data?.detail)
          ? error.response.data.detail[0]?.msg
          : error?.response?.data?.detail) ||
        error?.message ||
        "Could not create account.";

      Alert.alert("Registration Failed", apiMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.container}
      >
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.mainContent}>
            <View style={styles.headerSection}>
              <Text style={styles.title}>Create Account</Text>
              <Text style={styles.subtitle}>Join VectoFit today</Text>
            </View>

            <View style={styles.formContainer}>
              <View style={styles.inputGroup}>
                <Text style={styles.label}>Email or Username</Text>
                <TextInput
                  style={styles.input}
                  value={identifier}
                  onChangeText={setIdentifier}
                  autoCapitalize="none"
                  autoCorrect={false}
                  placeholder="Choose username or enter email"
                  placeholderTextColor="#71717A"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Password</Text>
                <TextInput
                  style={styles.input}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  placeholder="Create a password"
                  placeholderTextColor="#71717A"
                />
              </View>

              <Pressable
                style={[styles.button, loading && styles.buttonDisabled]}
                onPress={handleRegister}
                disabled={loading}
              >
                <Text style={styles.buttonText}>
                  {loading ? "Registering..." : "Register"}
                </Text>
              </Pressable>
            </View>
          </View>

          <View style={styles.footerSection}>
            <Text style={styles.footerText}>Already have an account?</Text>
            <Pressable
              onPress={() => navigation.navigate("Login")}
              hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
            >
              <Text style={styles.linkText}>Login</Text>
            </Pressable>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
