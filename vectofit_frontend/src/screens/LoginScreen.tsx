import React, { useState } from "react";
import {
  View,
  Text,
  Pressable,
  TextInput,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../navigation/types";
import useAuthStore from "../stores/useAuthStore";
import { authStyles as styles } from "../styles/LoginScreenStyles";

interface LoginForm {
  username: string;
  password: string;
}

export default function Login({ navigation }: LoginProps) {
  const [formData, setFormData] = useState<LoginForm>({
    username: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);

  const login = useAuthStore((state) => state.login);

  const handleLogin = async () => {
    if (!formData.username || !formData.password) {
      Alert.alert("Error", "Please fill in both fields.");
      return;
    }

    try {
      setLoading(true);
      await login(formData.username, formData.password);
    } catch (error) {
      Alert.alert("Login Failed", "Invalid username or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.container}
      >
        <View style={styles.headerSection}>
          <Text style={styles.title}>VectoFit</Text>
          <Text style={styles.subtitle}>Sign in to continue</Text>
        </View>

        <View style={styles.formContainer}>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Username</Text>
            <TextInput
              style={styles.input}
              value={formData.username}
              onChangeText={(text) =>
                setFormData({ ...formData, username: text })
              }
              autoCapitalize="none"
              placeholder="Enter your username"
              placeholderTextColor="#71717A"
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Password</Text>
            <TextInput
              style={styles.input}
              value={formData.password}
              onChangeText={(text) =>
                setFormData({ ...formData, password: text })
              }
              secureTextEntry
              placeholder="Enter your password"
              placeholderTextColor="#71717A"
            />
          </View>

          <Pressable
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={loading}
          >
            <Text style={styles.buttonText}>
              {loading ? "Logging in..." : "Login"}
            </Text>
          </Pressable>
        </View>

        <View style={styles.footerSection}>
          <Text style={styles.footerText}>Don't have an account?</Text>
          <Pressable onPress={() => navigation.navigate("Register")}>
            <Text style={styles.linkText}>Create account</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

type LoginProps = NativeStackScreenProps<RootStackParamList, "Login">;
