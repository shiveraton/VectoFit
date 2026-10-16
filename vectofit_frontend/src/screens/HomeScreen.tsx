import React, { useState } from "react";
import { View, Text, Pressable, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

import { RootStackParamList, BodyProfileData } from "../navigation/types";

import PhysicalInfoSection from "../components/home/PhysicalInfoSection";
import ThisWeekSection from "../components/home/ThisWeekSection";
import { capitalize } from "../utils/formatters";
import useAuthStore from "../stores/useAuthStore";
import styles from "../styles/HomeScreenStyles";

interface UserState {
  name: string;
  age: number;
  weight: number | null;
  height: number | null;
  left_lower_limb: number;
  right_lower_limb: number;
  trunk: number;
  this_week: string;
  last_session: Date;
  improvement: string;
  squats_completed: number;
}

export default function HomeScreen({ navigation }: HomeScreenProps) {
  const authUser = useAuthStore((state) => state.user);

  const [bodyProfileData, setBodyProfileData] = useState<BodyProfileData>({
    shoulder_width: 0,
    hip_width: 0,
    left_femur: 0,
    right_femur: 0,
    left_tibia: 0,
    right_tibia: 0,
  });

  return (
    <ScrollView
      style={styles.scrollView}
      contentContainerStyle={styles.scrollContent}
    >
      <Text style={styles.headerContainer}>Home Screen</Text>

      <Welcome username={authUser?.name} />

      <PhysicalInfoSection />

      <View style={styles.actionButtonsGroup}>
        <BodyAssessment
          navigation={navigation}
          bodyProfileData={bodyProfileData}
        />

        <SquatExercise navigation={navigation} />
      </View>

      <ThisWeekSection />
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

interface BodyAssessmentProp {
  navigation: HomeScreenProps["navigation"];
  bodyProfileData: BodyProfileData;
}

function BodyAssessment({ navigation, bodyProfileData }: BodyAssessmentProp) {
  const handleSubmit = () => {
    navigation.navigate("MorphologicalCalibration", {
      bodyProfileData,
    });
  };

  return (
    <Pressable style={styles.btnPrimary} onPress={handleSubmit}>
      <Text style={styles.btnPrimaryText}>Take Body Assessment</Text>
    </Pressable>
  );
}

interface SquatExerciseProps {
  navigation: HomeScreenProps["navigation"];
}

function SquatExercise({ navigation }: SquatExerciseProps) {
  const handleSubmit = () => {
    navigation.navigate("CameraPose", {
      exercise: "bodyweight_squat",
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

// Vecto Snapshot Section: probably later if there will be an exercises route
