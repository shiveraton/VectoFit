import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StatusBar,
  Text,
  View,
  StyleSheet,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useFocusEffect } from "@react-navigation/native";

import type { InsightsStackParamList } from "../navigation/insightsTypes";
import {
  getAssessmentErrorMessage,
  getAssessmentSessions,
  type AssessmentSessionSummary,
  type AssessmentStatus,
} from "../features/assessment/services/sessionStructure";
import styles from "../styles/SessionHistoryScreenStyles";
import { COLORS } from "../styles/designTokens";

type Props = NativeStackScreenProps<InsightsStackParamList, "SessionHistory">;
type StatusFilter = "ALL" | "COMPLETED" | "PROCESSING" | "FAILED";

const FILTERS: Array<{ label: string; value: StatusFilter }> = [
  { label: "All sessions", value: "ALL" },
  { label: "Completed", value: "COMPLETED" },
  { label: "In progress", value: "PROCESSING" },
  { label: "Failed", value: "FAILED" },
];

function formatDate(value: string): string {
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

function exerciseName(session: AssessmentSessionSummary): string {
  if (session.exercise_variant_name?.trim())
    return session.exercise_variant_name;
  return `Exercise variant #${session.exercise_variant}`;
}

function statusPresentation(status: string): {
  label: string;
  color: string;
  background: string;
} {
  switch (status as AssessmentStatus) {
    case "COMPLETED":
      return {
        label: "Completed",
        color: COLORS.successGreen,
        background: COLORS.successBg,
      };
    case "PROCESSING":
      return {
        label: "Processing",
        color: COLORS.warningYellow,
        background: "rgba(245, 158, 11, 0.14)",
      };
    case "PENDING":
      return {
        label: "Pending",
        color: COLORS.textSecondary,
        background: COLORS.inputBg,
      };
    case "FAILED":
      return {
        label: "Failed",
        color: COLORS.crimsonRed,
        background: COLORS.crimsonRedGlow,
      };
    default:
      return {
        label: status || "Unknown",
        color: COLORS.textSecondary,
        background: COLORS.inputBg,
      };
  }
}

export default function InsightsScreen({ navigation }: Props) {
  const [sessions, setSessions] = useState<AssessmentSessionSummary[]>([]);
  const [filter, setFilter] = useState<StatusFilter>("ALL");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const result = await getAssessmentSessions();
      setSessions(result);
    } catch (loadError) {
      setError(getAssessmentErrorMessage(loadError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void loadSessions();
      return undefined;
    }, [loadSessions]),
  );

  const visibleSessions = useMemo(() => {
    if (filter === "ALL") return sessions;
    if (filter === "PROCESSING") {
      return sessions.filter(
        (session) =>
          session.status === "PROCESSING" || session.status === "PENDING",
      );
    }
    return sessions.filter((session) => session.status === filter);
  }, [filter, sessions]);

  const statusCounts = useMemo(
    () => ({
      ALL: sessions.length,
      COMPLETED: sessions.filter((item) => item.status === "COMPLETED").length,
      PROCESSING: sessions.filter(
        (item) => item.status === "PROCESSING" || item.status === "PENDING",
      ).length,
      FAILED: sessions.filter((item) => item.status === "FAILED").length,
    }),
    [sessions],
  );

  const renderSession = useCallback(
    ({ item }: { item: AssessmentSessionSummary }) => {
      const status = statusPresentation(item.status);
      const canOpenResult =
        item.status === "COMPLETED" || item.status === "FAILED";

      return (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Open ${exerciseName(item)}, session ${item.id}`}
          onPress={() =>
            navigation.navigate("SessionResult", { sessionId: item.id })
          }
          style={({ pressed }) => [
            styles.sessionCard,
            pressed && styles.sessionCardPressed,
          ]}
        >
          <View style={styles.sessionCardTop}>
            <View style={styles.sessionIcon}>
              <Text style={styles.sessionIconText}>SQ</Text>
            </View>
            <View style={styles.sessionMain}>
              <Text style={styles.sessionTitle} numberOfLines={1}>
                {exerciseName(item)}
              </Text>
              <Text style={styles.sessionDate}>
                {formatDate(item.created_at)}
              </Text>
            </View>
            <View
              style={[
                styles.statusPill,
                { backgroundColor: status.background },
              ]}
            >
              <Text style={[styles.statusPillText, { color: status.color }]}>
                {status.label}
              </Text>
            </View>
          </View>

          <View style={styles.sessionCardFooter}>
            <View style={styles.sessionMetadata}>
              <Text style={styles.metadataValue}>{item.rep_count ?? 0}</Text>
              <Text style={styles.metadataLabel}>reps detected</Text>
            </View>
            <Text
              style={[
                styles.openSessionLabel,
                !canOpenResult && styles.openSessionLabelMuted,
              ]}
            >
              {canOpenResult ? "View results  ›" : "Details  ›"}
            </Text>
          </View>
          {item.status === "FAILED" && item.error_message ? (
            <Text style={styles.sessionError} numberOfLines={2}>
              {item.error_message}
            </Text>
          ) : null}
        </Pressable>
      );
    },
    [navigation],
  );

  const listHeader = (
    <View>
      <View style={styles.header}>
        <View style={styles.headerTextGroup}>
          <Text style={styles.eyebrow}>YOUR TRAINING HISTORY</Text>
          <Text style={styles.title}>Insights</Text>
          <Text style={styles.subtitle}>
            Review a session or revisit its movement findings.
          </Text>
        </View>
        <View style={styles.countBadge}>
          <Text style={styles.countNumber}>{sessions.length}</Text>
          <Text style={styles.countLabel}>sessions</Text>
        </View>
      </View>

      <Text style={styles.sectionTitle}>Session repository</Text>
      <FlatList
        horizontal
        data={FILTERS}
        keyExtractor={(item) => item.value}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filterList}
        renderItem={({ item }) => {
          const selected = filter === item.value;
          const count = statusCounts[item.value];
          return (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected }}
              onPress={() => setFilter(item.value)}
              style={[styles.filterChip, selected && styles.filterChipSelected]}
            >
              <Text
                style={[
                  styles.filterText,
                  selected && styles.filterTextSelected,
                ]}
              >
                {item.label} · {count}
              </Text>
            </Pressable>
          );
        }}
      />
      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorTitle}>Couldn’t load sessions</Text>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable
            style={styles.retryButton}
            onPress={() => void loadSessions()}
          >
            <Text style={styles.retryButtonText}>Try again</Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      <StatusBar barStyle="light-content" />
      {loading ? (
        <View style={styles.centerState}>
          <ActivityIndicator size="large" color={COLORS.primaryOrange} />
          <Text style={styles.stateTitle}>Loading your sessions</Text>
          <Text style={styles.stateDescription}>
            Retrieving saved assessment records.
          </Text>
        </View>
      ) : (
        <FlatList
          data={visibleSessions}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderSession}
          ListHeaderComponent={listHeader}
          ListEmptyComponent={
            error ? undefined : (
              <View style={styles.emptyState}>
                <View style={styles.emptyIcon}>
                  <Text style={styles.emptyIconText}>↗</Text>
                </View>
                <Text style={styles.stateTitle}>
                  {sessions.length === 0
                    ? "No sessions yet"
                    : "No matching sessions"}
                </Text>
                <Text style={styles.stateDescription}>
                  {sessions.length === 0
                    ? "Completed squat assessments will appear here after they are saved."
                    : "Try another filter to find a session."}
                </Text>
              </View>
            )
          }
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => void loadSessions(true)}
              tintColor={COLORS.primaryOrange}
              colors={[COLORS.primaryOrange]}
            />
          }
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
        />
      )}
    </SafeAreaView>
  );
}
