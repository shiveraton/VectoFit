import React from "react";
import { View, Text, TouchableOpacity, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import useAuthStore from "../stores/useAuthStore";
import styles from "../styles/ProfileScreenStyles";
import { COLORS } from "../styles/HomeScreenStyles";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RootStackParamList } from "../navigation/types";

const ProfileScreen = () => {
  const { user, logout } = useAuthStore();
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

  const handleLogout = () => {
    logout();
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 48 }}>
        <View style={styles.header}>
          <View style={styles.avatarContainer}>
            <Text style={styles.avatarText}>
              {user?.name?.charAt(0).toUpperCase() || "U"}
            </Text>
          </View>

          <View style={styles.userInfo}>
            <Text style={styles.userName}>{user?.name || "Your account"}</Text>
            <Text style={styles.userEmail}>
              {user?.email || "No email added"}
            </Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account Settings</Text>
          <View style={styles.card}>
            <TouchableOpacity style={styles.menuItem} accessibilityRole="button" onPress={() => navigation.navigate("EditProfile")}>
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemText}>Edit Profile</Text>
              </View>
              <Text style={{ color: COLORS.textSecondary }}>→</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.menuItem} accessibilityRole="button" onPress={() => navigation.navigate("Notifications")}>
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemText}>Notifications</Text>
              </View>
              <Text style={{ color: COLORS.textSecondary }}>→</Text>
            </TouchableOpacity>

            <TouchableOpacity style={[styles.menuItem, styles.menuItemLast]} accessibilityRole="button" onPress={() => navigation.navigate("PrivacySecurity")}>
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemText}>Privacy & Security</Text>
              </View>
              <Text style={{ color: COLORS.textSecondary }}>→</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Support</Text>

          <View style={styles.card}>
            <TouchableOpacity style={[styles.menuItem, styles.menuItemLast]} accessibilityRole="button" onPress={() => navigation.navigate("HelpSupport")}>
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemText}>Help & Support</Text>
              </View>
              <Text style={{ color: COLORS.textSecondary }}>→</Text>
            </TouchableOpacity>
          </View>
        </View>

        <TouchableOpacity style={styles.logoutButton} accessibilityRole="button" onPress={handleLogout}>
          <Text style={styles.logoutButtonText}>Log Out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

export default ProfileScreen;
