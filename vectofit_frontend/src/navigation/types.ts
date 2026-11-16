import type { NavigatorScreenParams } from "@react-navigation/native";
import type { InsightsStackParamList } from "./insightsTypes";

export interface BodyProfileData {
  shoulder_width: number;
  hip_width: number;
  left_femur: number;
  right_femur: number;
  left_tibia: number;
  right_tibia: number;
}

export type SquatExerciseType =
  | "bodyweight_squat"
  | "goblet_squat"
  | "barbell_squat";

export type AssessmentViewAngle = "diagonal" | "frontal" | "sagittal";

export type RootStackParamList = {
  MainTabs: NavigatorScreenParams<{
    Home: undefined;
    Insights: NavigatorScreenParams<InsightsStackParamList>;
    Profile: undefined;
  }> | undefined;
  EditProfile: undefined;
  Notifications: undefined;
  PrivacySecurity: undefined;
  HelpSupport: undefined;
  WorkoutSession: undefined;
  Home: undefined;
  Login: undefined;
  Register: undefined;
  CameraPose: {
    exercise: SquatExerciseType;
    viewAngle?: AssessmentViewAngle;
  };
  MorphologicalCalibration: {
    bodyProfileData?: BodyProfileData;
    userHeightCm?: number;
  };
  Insights: undefined;
  Profile: undefined;
};
