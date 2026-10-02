import React, { useState } from "react";
import { View, Text, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../navigation/types";
import styles, { COLORS } from "../styles/InsightsScreenStyles";

export interface JointAngleAnalysis {
  trunk: number;
  hip: number;
  knee: number;
  ankle: number;
}

export interface RangeOfMotion {
  target: number;
  average: number;
  best: number;
}

export interface KinematicVelocityTracking {
  descent_speed: number;
  ascent_speed: number;
  fastest_rep: number;
  slowest_rep: number;
}

export interface BilateralAsymmetryDetection {
  left_lower_limb: number;
  right_lower_limb: number;
  difference: number;
}

export interface SessionSummary {
  overall_score: number;
  squat_type: string;
  set_count: number;
  rep_count: number;
  duration: number;
}

export interface RepConsistency {
  rep_quality: number;
  consistency: number;
}

export interface DetectedIssues {
  common_errors: string[];
  neutral_spine: string;
}

export interface TrendItem {
  id: string;
  feature: string;
  direction: "improved" | "declined";
  change: number;
  unit: "°" | "%" | "m/s";
}

type InsightsScreenProps = NativeStackScreenProps<
  RootStackParamList,
  "Insights"
>;

export default function Insights({ route }: InsightsScreenProps) {
  const [jointAngleAnalysis] = useState<JointAngleAnalysis>({
    trunk: 42,
    hip: 108,
    knee: 115,
    ankle: 28,
  });

  const [rangeOfMotion] = useState<RangeOfMotion>({
    target: 110,
    average: 106,
    best: 114,
  });

  const [kinematicVelocity] = useState<KinematicVelocityTracking>({
    descent_speed: 0.45,
    ascent_speed: 0.62,
    fastest_rep: 0.71,
    slowest_rep: 0.48,
  });

  const [bilateralAsymmetry] = useState<BilateralAsymmetryDetection>({
    left_lower_limb: 51.2,
    right_lower_limb: 48.8,
    difference: 2.4,
  });

  const [sessionSummary] = useState<SessionSummary>({
    overall_score: 92,
    squat_type: "Barbell Back Squat",
    set_count: 4,
    rep_count: 32,
    duration: 18,
  });

  const [repConsistency] = useState<RepConsistency>({
    rep_quality: 88,
    consistency: 94,
  });

  const [detectedIssues] = useState<DetectedIssues>({
    common_errors: ["Minor Knee Valgus on Rep 7", "Slight Heel Lift"],
    neutral_spine: "Maintained",
  });

  const [trends] = useState<TrendItem[]>([
    {
      id: "1",
      feature: "Squat Depth (ROM)",
      direction: "improved",
      change: 4.2,
      unit: "°",
    },
    {
      id: "2",
      feature: "Bilateral Balance",
      direction: "improved",
      change: 1.8,
      unit: "%",
    },
    {
      id: "3",
      feature: "Ascent Velocity",
      direction: "declined",
      change: 0.05,
      unit: "m/s",
    },
  ]);

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header Section */}
        <View style={styles.headerContainer}>
          <View style={styles.headerTextGroup}>
            <Text style={styles.greetingSubtitle}>Analytics Repository</Text>
            <Text style={styles.userNameTitle}>Insights</Text>
          </View>
        </View>

        {/* Hero Session Summary */}
        <SessionSummaryCard session_summary={sessionSummary} />

        {/* Biomechanics Module Cards */}
        <JointAngleAnalysisCard joint_angle_analysis={jointAngleAnalysis} />
        <RangeOfMotionCard range_of_motion={rangeOfMotion} />
        <BilateralAsymmetryCard
          bilateral_asymmetry_detection={bilateralAsymmetry}
        />
        <KinematicVelocityTrackingCard
          kinematic_velocity_tracking={kinematicVelocity}
        />

        {/* Form Quality & Diagnostics */}
        <FormDiagnosticsCard
          rep_consistency={repConsistency}
          detected_issues={detectedIssues}
        />

        {/* Performance Trends */}
        <PerformanceTrend trends={trends} />
      </ScrollView>
    </SafeAreaView>
  );
}

// Sub-components

const SessionSummaryCard: React.FC<{ session_summary: SessionSummary }> = ({
  session_summary,
}) => (
  <View style={styles.card}>
    <View style={styles.cardHeaderRow}>
      <Text style={styles.cardTitle}>Session Overview</Text>
    </View>

    <View style={styles.scoreHighlightCard}>
      <Text style={styles.scoreHighlightLabel}>Form Quality Index</Text>
      <Text style={styles.scoreHighlightValue}>
        {session_summary.overall_score}%
      </Text>
      <Text style={styles.scoreHighlightSubtext}>
        Optimal depth & hip extension maintained
      </Text>
    </View>

    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Exercise</Text>
      <Text style={styles.metricValue}>{session_summary.squat_type}</Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Sets Completed</Text>
      <Text style={styles.metricValue}>{session_summary.set_count}</Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Total Reps</Text>
      <Text style={styles.metricValue}>{session_summary.rep_count}</Text>
    </View>
    <View style={styles.metricRowLast}>
      <Text style={styles.metricLabel}>Session Duration</Text>
      <Text style={styles.metricValue}>{session_summary.duration} mins</Text>
    </View>
  </View>
);

const JointAngleAnalysisCard: React.FC<{
  joint_angle_analysis: JointAngleAnalysis;
}> = ({ joint_angle_analysis }) => (
  <View style={[styles.card, styles.cardJAA]}>
    <View style={styles.cardHeaderRow}>
      <Text style={styles.cardTitle}>Joint Angle Analysis</Text>
      <View style={[styles.moduleBadge, styles.badgeJAA]}>
        <Text style={[styles.moduleBadgeText, { color: COLORS.jaaColor }]}>
          JAA
        </Text>
      </View>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Trunk Inclination</Text>
      <Text style={styles.metricValueJAA}>{joint_angle_analysis.trunk}°</Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Hip Flexion Angle</Text>
      <Text style={styles.metricValueJAA}>{joint_angle_analysis.hip}°</Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Knee Flexion Angle</Text>
      <Text style={styles.metricValueJAA}>{joint_angle_analysis.knee}°</Text>
    </View>
    <View style={styles.metricRowLast}>
      <Text style={styles.metricLabel}>Ankle Dorsiflexion</Text>
      <Text style={styles.metricValueJAA}>{joint_angle_analysis.ankle}°</Text>
    </View>
  </View>
);

const RangeOfMotionCard: React.FC<{ range_of_motion: RangeOfMotion }> = ({
  range_of_motion,
}) => (
  <View style={[styles.card, styles.cardROM]}>
    <View style={styles.cardHeaderRow}>
      <Text style={styles.cardTitle}>Range of Motion</Text>
      <View style={[styles.moduleBadge, styles.badgeROM]}>
        <Text style={[styles.moduleBadgeText, { color: COLORS.romColor }]}>
          ROM
        </Text>
      </View>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Target Depth</Text>
      <Text style={styles.metricValueROM}>{range_of_motion.target}°</Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Average Depth</Text>
      <Text style={styles.metricValueROM}>{range_of_motion.average}°</Text>
    </View>
    <View style={styles.metricRowLast}>
      <Text style={styles.metricLabel}>Best Depth Achieved</Text>
      <Text style={styles.metricValueROM}>{range_of_motion.best}°</Text>
    </View>
  </View>
);

const BilateralAsymmetryCard: React.FC<{
  bilateral_asymmetry_detection: BilateralAsymmetryDetection;
}> = ({ bilateral_asymmetry_detection }) => (
  <View style={[styles.card, styles.cardBAD]}>
    <View style={styles.cardHeaderRow}>
      <Text style={styles.cardTitle}>Bilateral Asymmetry</Text>
      <View style={[styles.moduleBadge, styles.badgeBAD]}>
        <Text style={[styles.moduleBadgeText, { color: COLORS.badColor }]}>
          BAD
        </Text>
      </View>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Left Lower Limb Load</Text>
      <Text style={styles.metricValueBAD}>
        {bilateral_asymmetry_detection.left_lower_limb}%
      </Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Right Lower Limb Load</Text>
      <Text style={styles.metricValueBAD}>
        {bilateral_asymmetry_detection.right_lower_limb}%
      </Text>
    </View>
    <View style={styles.metricRowLast}>
      <Text style={styles.metricLabel}>Difference Variance</Text>
      <Text style={styles.metricValueBAD}>
        {bilateral_asymmetry_detection.difference}%
      </Text>
    </View>
  </View>
);

const KinematicVelocityTrackingCard: React.FC<{
  kinematic_velocity_tracking: KinematicVelocityTracking;
}> = ({ kinematic_velocity_tracking }) => (
  <View style={[styles.card, styles.cardKVT]}>
    <View style={styles.cardHeaderRow}>
      <Text style={styles.cardTitle}>Kinematic Velocity</Text>
      <View style={[styles.moduleBadge, styles.badgeKVT]}>
        <Text style={[styles.moduleBadgeText, { color: COLORS.kvtColor }]}>
          KVT
        </Text>
      </View>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Descent Speed (Eccentric)</Text>
      <Text style={styles.metricValueKVT}>
        {kinematic_velocity_tracking.descent_speed} m/s
      </Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Ascent Speed (Concentric)</Text>
      <Text style={styles.metricValueKVT}>
        {kinematic_velocity_tracking.ascent_speed} m/s
      </Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Fastest Rep Speed</Text>
      <Text style={styles.metricValueKVT}>
        {kinematic_velocity_tracking.fastest_rep} m/s
      </Text>
    </View>
    <View style={styles.metricRowLast}>
      <Text style={styles.metricLabel}>Slowest Rep Speed</Text>
      <Text style={styles.metricValueKVT}>
        {kinematic_velocity_tracking.slowest_rep} m/s
      </Text>
    </View>
  </View>
);

const FormDiagnosticsCard: React.FC<{
  rep_consistency: RepConsistency;
  detected_issues: DetectedIssues;
}> = ({ rep_consistency, detected_issues }) => (
  <View style={styles.card}>
    <View style={styles.cardHeaderRow}>
      <Text style={styles.cardTitle}>Form Quality & Diagnostics</Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Rep Quality Score</Text>
      <Text style={styles.metricValue}>{rep_consistency.rep_quality}%</Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Bar Path Consistency</Text>
      <Text style={styles.metricValue}>{rep_consistency.consistency}%</Text>
    </View>
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>Spine Alignment</Text>
      <Text style={[styles.metricValue, { color: COLORS.successGreen }]}>
        {detected_issues.neutral_spine}
      </Text>
    </View>
    <View style={styles.diagnosticBox}>
      <Text style={styles.diagnosticLabel}>Detected Deviations:</Text>
      {detected_issues.common_errors.map((error, idx) => (
        <Text key={idx} style={styles.diagnosticBullet}>
          • {error}
        </Text>
      ))}
    </View>
  </View>
);

const PerformanceTrend: React.FC<{ trends: TrendItem[] }> = ({ trends }) => (
  <View style={styles.card}>
    <View style={styles.cardHeaderRow}>
      <Text style={styles.cardTitle}>Longitudinal Trends</Text>
    </View>
    {trends.map((item) => {
      const isImproved = item.direction === "improved";
      return (
        <View key={item.id} style={styles.trendRow}>
          <Text style={styles.trendFeature}>{item.feature}</Text>
          <Text
            style={isImproved ? styles.trendImproved : styles.trendDeclined}
          >
            {isImproved ? "▲ +" : "▼ -"}
            {item.change}
            {item.unit}
          </Text>
        </View>
      );
    })}
  </View>
);
