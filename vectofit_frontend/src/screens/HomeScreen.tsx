import React, { useState, useEffect } from "react";
import { View, Text, Pressable, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../navigation/types";
import { getProfiles } from "../features/profile/services/profileService";
import { capitalize } from "../utils/formatters";
import axios from "axios";
import authStore from "../stores/authStore";
import styles from "../styles/HomeScreenStyles";

interface UserState {
  name: string;
  age: number;
  weight: number;
  height: number;
  left_lower_limb: number;
  right_lower_limb: number;
  trunk: number;
  this_week: string;
  last_session: Date;
  improvement: string;
  squats_completed: number;
}

interface Exercise {
  bodyweight_squat: string;
  goblet_squat: string;
  barbell_squat: string;
}

export default function HomeScreen({ navigation }: HomeScreenProps) {
  const authUser = authStore((state) => state.user);

  const [userData, setUserData] = useState({
    name: "",
    age: 0,
    weight: 0,
    height: 0,
    left_lower_limb: 0,
    right_lower_limb: 0,
    trunk: 0,
    this_week: "",
    last_session: new Date(),
    improvement: "No improvement data yet",
    squats_completed: 0,
  });

  const [exercise] = useState<Exercise>({
    bodyweight_squat: "",
    goblet_squat: "",
    barbell_squat: "",
  });

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const profiles = await getProfiles();
        console.log("Profiles:", profiles);
      } catch (error) {
        if (axios.isAxiosError(error)) {
          console.error("Profile request failed:", error.response?.status);
          console.error("Request URL:", error.config?.url);
          console.error("Base URL:", error.config?.baseURL);
          console.error(
            "Django response:",
            String(error.response?.data).slice(0, 2000),
          );
        } else {
          console.error("Failed to load profile:", error);
        }
      }
    };
    loadProfile();
  }, []);

  return (
    <ScrollView
      style={styles.scrollView}
      contentContainerStyle={styles.scrollContent}
    >
      <Text style={styles.headerContainer}>Home Screen</Text>
      <Welcome username={authUser?.name} />
      <PhysicalInformation user={userData} />

      <View style={styles.actionButtonsGroup}>
        <BodyAssessment user={userData} />
        <SquatExercise exercise={exercise} navigation={navigation} />
      </View>

      <ThisWeek user={userData} />
    </ScrollView>
  );
}

type HomeScreenProps = NativeStackScreenProps<RootStackParamList, "Home">;

interface WelcomeProps {
  username?: string;
}

function Welcome({ username }: WelcomeProps) {
  return (
    <View style={styles.headerContainer}>
      <View style={styles.headerTextGroup}>
        <Text style={styles.greetingSubtitle}>Welcome back</Text>

        <Text style={styles.userNameTitle}>{capitalize(username)}</Text>
      </View>

      <View style={styles.brandBadge}>
        <Text style={styles.brandBadgeText}>VECTOFIT</Text>
      </View>
    </View>
  );
}

interface PhysicalInformationProps {
  user: {
    weight: number;
    height: number;
  };
}

function PhysicalInformation({ user }: PhysicalInformationProps) {
  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>Physical Information</Text>

        <View style={[styles.statusChip, styles.statusChipUncalibrated]}>
          <View style={[styles.statusDot, styles.statusDotUncalibrated]} />

          <Text style={[styles.statusText, styles.statusTextUncalibrated]}>
            Not Calibrated
          </Text>
        </View>
      </View>

      <View style={styles.inputsGrid}>
        <View style={styles.inputCol}>
          <Text style={styles.inputLabel}>Weight</Text>

          <View style={styles.textInput}>
            <Text style={styles.infoText}>{user.weight || "0"} kg</Text>
          </View>
        </View>

        <View style={styles.inputCol}>
          <Text style={styles.inputLabel}>Height</Text>

          <View style={styles.textInput}>
            <Text style={styles.infoText}>{user.height || "0"} cm</Text>
          </View>
        </View>
      </View>

      <View style={styles.bmiDisplayCard}>
        <View style={styles.bmiLabelGroup}>
          <Text style={styles.bmiLabel}>BMI</Text>

          <Text style={styles.bmiSubtext}>
            Based on your physical information
          </Text>
        </View>

        <Text style={styles.bmiValue}>--</Text>
      </View>
    </View>
  );
}

interface BodyAssessmentProp {
  user: {
    left_lower_limb: number;
    right_lower_limb: number;
    trunk: number;
  };
}

function BodyAssessment({ user }: BodyAssessmentProp) {
  const handleSubmit = () => {
    // navigation or api call
  };

  return (
    <Pressable style={styles.btnPrimary} onPress={handleSubmit}>
      <Text style={styles.btnPrimaryText}>Take Body Assessment</Text>
    </Pressable>
  );
}

interface SquatExerciseProps {
  exercise: Exercise;
  navigation: HomeScreenProps["navigation"];
}

function SquatExercise({ exercise, navigation }: SquatExerciseProps) {
  const handleSubmit = () => {
    navigation.navigate("CameraPose", {
      exercise,
    });
  };

  return (
    <Pressable style={styles.btnSecondary} onPress={handleSubmit}>
      <Text style={styles.btnSecondaryText}>Start Squat Exercise</Text>
    </Pressable>
  );
}

interface ThisWeekProps {
  user: UserState;
}

function ThisWeek({ user }: ThisWeekProps) {
  return (
    <View style={styles.card}>
      <View style={styles.trendHeaderRow}>
        <Text style={styles.cardTitle}>This Week</Text>
      </View>

      <View style={styles.trendStatRow}>
        <Text style={styles.trendStatNumber}>{user.squats_completed}</Text>

        <Text style={styles.trendStatUnit}>squats completed</Text>
      </View>

      <Text style={styles.trendNoteText}>{user.improvement}</Text>

      <Text style={styles.emptyStateText}>
        Last Session: {user.last_session.toLocaleDateString()}
      </Text>
    </View>
  );
}

// Vecto Snapshot Section -> Actually I want this for the Exercises route.
