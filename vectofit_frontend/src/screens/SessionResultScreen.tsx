// SessionResultScreen.tsx

import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import type { InsightsStackParamList } from "../navigation/insightsTypes";
import {
  getAssessmentErrorMessage,
  getAssessmentSession,
  type AssessmentRep,
  type AssessmentSessionDetail,
} from "../features/assessment/services/assessmentSession";
import { COLORS } from "../styles/designTokens";
import styles from "../styles/SessionResultScreenStyles";

type Props = NativeStackScreenProps<InsightsStackParamList, "SessionResult">;
type JsonRecord = Record<string, unknown>;

const METRIC_LABELS: Record<string, string> = {
  hip_angle: "Hip angle",
  knee_angle: "Knee angle",
  trunk_angle: "Trunk angle observations",
  rom: "Range of motion",
  asymmetry: "Bilateral asymmetry",
  velocity: "Movement velocity",
};

function formatDate(value?: string | null): string {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function readableLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\bjaa\b/gi, "JAA")
    .replace(/\brom\b/gi, "ROM")
    .replace(/\bbad\b/gi, "BAD")
    .replace(/\bkvt\b/gi, "KVT")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatValue(value: unknown): string {
  if (typeof value === "number")
    return Number.isFinite(value) ? value.toFixed(2) : "Unavailable";
  if (typeof value === "string") return value || "Unavailable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) {
    const numeric = value.filter(
      (item): item is number =>
        typeof item === "number" && Number.isFinite(item),
    );
    if (numeric.length === value.length && numeric.length > 0) {
      const min = Math.min(...numeric);
      const max = Math.max(...numeric);
      const average =
        numeric.reduce((sum, item) => sum + item, 0) / numeric.length;
      return `avg ${average.toFixed(2)} · range ${min.toFixed(2)}–${max.toFixed(2)}`;
    }
    return `${value.length} values`;
  }
  if (value === null || value === undefined) return "Unavailable";
  return "Recorded";
}

function asRecord(value: unknown): JsonRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as JsonRecord)
    : null;
}

function statusMessage(
  session: AssessmentSessionDetail,
): { title: string; body: string; color: string } | null {
  if (session.status === "PENDING" || session.status === "PROCESSING") {
    return {
      title: "Assessment is still processing",
      body: "Rep analysis is not marked complete yet. Refresh this result later to retrieve the latest saved status.",
      color: COLORS.warningYellow,
    };
  }
  if (session.status === "FAILED") {
    return {
      title: "Assessment failed",
      body:
        session.error_message ||
        "The backend did not provide an error message for this session.",
      color: COLORS.crimsonRed,
    };
  }
  return null;
}

export default function SessionResultScreen({ route, navigation }: Props) {
  const { sessionId } = route.params;
  const [session, setSession] = useState<AssessmentSessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAssessmentSession(sessionId);
      setSession(result);
    } catch (loadError) {
      setError(getAssessmentErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
        <View style={styles.centerState}>
          <ActivityIndicator size="large" color={COLORS.primaryOrange} />
          <Text style={styles.stateTitle}>Loading session results</Text>
          <Text style={styles.stateDescription}>
            Retrieving session #{sessionId} and its saved rep analysis.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error || !session) {
    return (
      <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
        <View style={styles.centerState}>
          <Text style={styles.stateTitle}>Unable to open this session</Text>
          <Text style={styles.stateDescription}>
            {error ?? "The session was not found."}
          </Text>
          <Pressable
            style={styles.actionButton}
            onPress={() => void loadSession()}
          >
            <Text style={styles.actionButtonText}>Retry</Text>
          </Pressable>
          <Pressable
            style={styles.actionButton}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.actionButtonText}>Back to Insights</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const notice = statusMessage(session);
  const exerciseName = session.exercise_variant_name?.trim()
    ? session.exercise_variant_name
    : `Exercise variant #${session.exercise_variant}`;

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Back to session history"
            onPress={() => navigation.goBack()}
            style={styles.backButton}
          >
            <Text style={styles.backButtonText}>‹</Text>
          </Pressable>
          <View style={styles.headerText}>
            <Text style={styles.eyebrow}>SESSION REPOSITORY</Text>
            <Text style={styles.title}>Session #{session.id}</Text>
          </View>
        </View>

        <View style={styles.summaryCard}>
          <Text style={styles.exerciseName}>{exerciseName}</Text>
          <Text style={styles.dateText}>
            Recorded {formatDate(session.created_at)}
          </Text>
          <View style={styles.summaryDivider} />
          <View style={styles.summaryStats}>
            <View style={styles.summaryStat}>
              <Text style={styles.summaryStatValue}>
                {session.rep_count ?? session.reps?.length ?? 0}
              </Text>
              <Text style={styles.summaryStatLabel}>Reps detected</Text>
            </View>
            <View style={styles.summaryStat}>
              <Text
                style={[
                  styles.summaryStatValue,
                  { color: notice?.color ?? COLORS.successGreen },
                ]}
              >
                {readableLabel(session.status)}
              </Text>
              <Text style={styles.summaryStatLabel}>Session status</Text>
            </View>
          </View>
        </View>

        {notice ? (
          <View
            style={[
              styles.notice,
              {
                backgroundColor: `${notice.color}12`,
                borderColor: `${notice.color}66`,
              },
            ]}
          >
            <Text style={styles.noticeTitle}>{notice.title}</Text>
            <Text style={styles.noticeText}>{notice.body}</Text>
            {session.status !== "FAILED" ? (
              <Pressable
                style={styles.actionButton}
                onPress={() => void loadSession()}
              >
                <Text style={styles.actionButtonText}>Refresh session</Text>
              </Pressable>
            ) : null}
          </View>
        ) : null}

        <Text style={styles.sectionTitle}>Repetition analysis</Text>
        <Text style={styles.sectionSubtitle}>
          Each card is based on the saved analysis for that repetition. Missing
          score fields are left unavailable rather than estimated.
        </Text>

        {session.reps?.length ? (
          session.reps.map((rep) => <RepResultCard key={rep.id} rep={rep} />)
        ) : (
          <View style={styles.notice}>
            <Text style={styles.noticeTitle}>No repetition results saved</Text>
            <Text style={styles.noticeText}>
              {session.status === "COMPLETED"
                ? "The session is marked complete, but the API returned no repetition records."
                : "Repetition results will appear here when the session has saved rep assessments."}
            </Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function RepResultCard({ rep }: { rep: AssessmentRep }) {
  const analysis = asRecord(rep.analysis_result);
  const metrics = asRecord(analysis?.metrics) ?? {};
  const classifications = asRecord(analysis?.classifications) ?? {};
  const feedback = Array.isArray(analysis?.feedback)
    ? analysis.feedback.filter(
        (item): item is { metric?: string; message?: string } =>
          asRecord(item) !== null &&
          typeof (item as JsonRecord).message === "string",
      )
    : [];

  const metricEntries = Object.entries(metrics).filter(
    ([, value]) => value !== null && value !== undefined,
  );
  const classificationEntries = Object.entries(classifications)
    .map(([key, value]) => ({ key, value: asRecord(value) }))
    .filter((item) => item.value !== null);
  const scoreEntries: Array<[string, number | null]> = [
    ["JAA", rep.jaa_score],
    ["ROM", rep.rom_score],
    ["BAD", rep.bad_score],
    ["KVT", rep.kvt_score],
    ["Hybrid", rep.hybrid_score],
  ];
  const availableScores = scoreEntries.filter(
    (entry): entry is [string, number] => typeof entry[1] === "number",
  );
  const storedClassification = rep.classification?.trim();
  const repLabel =
    storedClassification ||
    (metricEntries.length > 0 ? "Analyzed" : "Unclassified");

  return (
    <View style={styles.repCard}>
      <View style={styles.repHeader}>
        <Text style={styles.repTitle}>Rep {rep.rep_number}</Text>
        <View style={styles.classificationPill}>
          <Text style={styles.classificationText} numberOfLines={1}>
            {readableLabel(repLabel)}
          </Text>
        </View>
      </View>

      {availableScores.length > 0 ? (
        <View style={styles.scoreRow}>
          {availableScores.map(([label, value]) => (
            <View key={label} style={styles.scoreChip}>
              <Text style={styles.scoreChipText}>
                {label}: {value.toFixed(1)}
              </Text>
            </View>
          ))}
        </View>
      ) : null}

      {metricEntries.length > 0 ? (
        <>
          <Text style={styles.blockTitle}>Measured metrics</Text>
          {metricEntries.map(([key, value]) => (
            <View key={key} style={styles.dataRow}>
              <Text style={styles.dataLabel}>
                {METRIC_LABELS[key] ?? readableLabel(key)}
              </Text>
              <Text style={styles.dataValue}>{formatValue(value)}</Text>
            </View>
          ))}
        </>
      ) : null}

      {classificationEntries.length > 0 ? (
        <>
          <Text style={styles.blockTitle}>Rule-based findings</Text>
          {classificationEntries.map(({ key, value }) => {
            const classification = value?.classification;
            const evaluation = asRecord(value?.evaluation);
            const detail =
              typeof classification === "string"
                ? readableLabel(classification)
                : "No classification";
            const evaluationText = evaluation
              ? Object.entries(evaluation)
                  .filter(
                    ([, item]) =>
                      typeof item === "number" || typeof item === "string",
                  )
                  .map(
                    ([name, item]) =>
                      `${readableLabel(name)}: ${formatValue(item)}`,
                  )
                  .join(" · ")
              : "";
            return (
              <View key={key} style={styles.dataRow}>
                <Text style={styles.dataLabel}>{readableLabel(key)}</Text>
                <View style={{ maxWidth: "60%", alignItems: "flex-end" }}>
                  <Text style={styles.dataValue}>{detail}</Text>
                  {evaluationText ? (
                    <Text
                      style={[
                        styles.dataLabel,
                        { textAlign: "right", marginTop: 3 },
                      ]}
                    >
                      {evaluationText}
                    </Text>
                  ) : null}
                </View>
              </View>
            );
          })}
        </>
      ) : null}

      {feedback.length > 0 ? (
        <>
          <Text style={styles.blockTitle}>Feedback</Text>
          {feedback.map((item, index) => (
            <View
              key={`${item.metric ?? "feedback"}-${index}`}
              style={styles.feedbackItem}
            >
              <Text style={styles.feedbackDot}>•</Text>
              <Text style={styles.feedbackText}>{item.message}</Text>
            </View>
          ))}
        </>
      ) : null}

      {metricEntries.length === 0 &&
      classificationEntries.length === 0 &&
      feedback.length === 0 ? (
        <Text style={styles.noticeText}>
          No structured analysis payload was saved for this repetition.
        </Text>
      ) : null}
    </View>
  );
}
