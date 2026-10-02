import React from "react";
import { View, Text, TouchableOpacity, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import authStore from "../stores/authStore";
import styles from "../styles/ProfileScreenStyles";
import { COLORS } from "../styles/HomeScreenStyles";
import { capitalize } from "../utils/formatters";

const ProfileScreen = () => {
  const { user, logout } = authStore();

  const handleLogout = () => {
    logout();
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <View style={styles.avatarContainer}>
            <Text style={styles.avatarText}>
              {user?.name?.charAt(0).toUpperCase() || "U"}
            </Text>
          </View>

          <View style={styles.userInfo}>
            <Text style={styles.userName}>{capitalize(user?.name)}</Text>
            <Text style={styles.userEmail}>
              {user?.email || "user@example.com"}
            </Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account Settings</Text>
          <View style={styles.card}>
            <TouchableOpacity style={styles.menuItem}>
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemText}>Edit Profile</Text>
              </View>
              <Text style={{ color: COLORS.textSecondary }}>→</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.menuItem}>
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemText}>Notifications</Text>
              </View>
              <Text style={{ color: COLORS.textSecondary }}>→</Text>
            </TouchableOpacity>

            <TouchableOpacity style={[styles.menuItem, styles.menuItemLast]}>
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemText}>Privacy & Security</Text>
              </View>
              <Text style={{ color: COLORS.textSecondary }}>→</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>App Preferences</Text>

          <View style={styles.card}>
            <TouchableOpacity style={styles.menuItem}>
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemText}>Units (Metric/Imperial)</Text>
              </View>
              <Text style={{ color: COLORS.textSecondary }}>→</Text>
            </TouchableOpacity>

            <TouchableOpacity style={[styles.menuItem, styles.menuItemLast]}>
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemText}>Help & Support</Text>
              </View>
              <Text style={{ color: COLORS.textSecondary }}>→</Text>
            </TouchableOpacity>
          </View>
        </View>

        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Text style={styles.logoutButtonText}>Log Out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

export default ProfileScreen;
