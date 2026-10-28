import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import axios from "axios";
import Svg, { Line, Rect, Text as SvgText } from "react-native-svg";

import apiClient from "../../api/client";
import { COLORS, RADIUS, SPACING } from "../../styles/HomeScreenStyles";

interface DailyActivityPoint {
  date: string;
  rep_count: number;
  session_count: number;
}

interface WeeklyTrendSummary {
  week_start: string;
  session_count: number;
  rep_count: number;
  avg_hybrid_score: number | null;
  previous_week_session_count: number;
  previous_week_rep_count: number;
  previous_week_avg_hybrid_score: number | null;
  daily_activity: DailyActivityPoint[];
}

const CHART_WIDTH = 336;
const CHART_HEIGHT = 184;
const PLOT_LEFT = 31;
const PLOT_RIGHT = 8;
const PLOT_TOP = 27;
const PLOT_BOTTOM = 29;
const BAR_WIDTH = 18;

function formatDate(
  value: string,
  options: Intl.DateTimeFormatOptions,
): string {
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-US", options);
}

function addDaysToDateString(value: string, offset: number): string {
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  date.setDate(date.getDate() + offset);

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getLocalDateString(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 401) {
      return "Your session may have expired. Sign in again to load your weekly activity.";
    }
    if (error.response) {
      return `Weekly activity request failed (${error.response.status}). Try refreshing.`;
    }
    return "Couldn't reach the server. Check your connection and try again.";
  }

  if (error instanceof Error) return error.message;
  return "An unexpected error occurred while loading weekly activity.";
}

function isDailyActivityPoint(value: unknown): value is DailyActivityPoint {
  if (!value || typeof value !== "object") return false;
  const point = value as Partial<DailyActivityPoint>;

  return (
    typeof point.date === "string" &&
    /^\d{4}-\d{2}-\d{2}$/.test(point.date) &&
    typeof point.rep_count === "number" &&
    Number.isFinite(point.rep_count) &&
    point.rep_count >= 0 &&
    typeof point.session_count === "number" &&
    Number.isFinite(point.session_count) &&
    point.session_count >= 0
  );
}

function isWeeklyTrendSummary(value: unknown): value is WeeklyTrendSummary {
  if (!value || typeof value !== "object") return false;

  const summary = value as Partial<WeeklyTrendSummary>;
  const isFiniteNumber = (candidate: unknown): candidate is number =>
    typeof candidate === "number" && Number.isFinite(candidate);

  const isNullableFiniteNumber = (
    candidate: unknown,
  ): candidate is number | null =>
    candidate === null || isFiniteNumber(candidate);

  return (
    typeof summary.week_start === "string" &&
    isFiniteNumber(summary.session_count) &&
    isFiniteNumber(summary.rep_count) &&
    isFiniteNumber(summary.previous_week_session_count) &&
    isFiniteNumber(summary.previous_week_rep_count) &&
    isNullableFiniteNumber(summary.avg_hybrid_score) &&
    isNullableFiniteNumber(summary.previous_week_avg_hybrid_score) &&
    Array.isArray(summary.daily_activity) &&
    summary.daily_activity.every(isDailyActivityPoint)
  );
}

function WeeklyActivityChart({
  weekStart,
  data,
}: {
  weekStart: string;
  data: DailyActivityPoint[];
}) {
  const activityByDate = new Map(data.map((point) => [point.date, point]));
  const points: DailyActivityPoint[] = Array.from({ length: 7 }, (_, index) => {
    const date = addDaysToDateString(weekStart, index);
    return (
      activityByDate.get(date) ?? {
        date,
        rep_count: 0,
        session_count: 0,
      }
    );
  });

  const maxValue = Math.max(1, ...points.map((point) => point.rep_count));
  const plotWidth = CHART_WIDTH - PLOT_LEFT - PLOT_RIGHT;
  const plotHeight = CHART_HEIGHT - PLOT_TOP - PLOT_BOTTOM;
  const slotWidth = plotWidth / 7;
  const today = getLocalDateString();
  const hasReps = points.some((point) => point.rep_count > 0);
  const ticks = Array.from(
    new Set([0, Math.ceil(maxValue / 2), maxValue]),
  ).sort((a, b) => a - b);

  return (
    <View style={styles.chartContainer}>
      <View style={styles.chartHeadingRow}>
        <View>
          <Text style={styles.chartTitle}>Daily repetitions</Text>
          <Text style={styles.chartDescription}>
            Your activity from Monday to Sunday
          </Text>
        </View>
        <View style={styles.chartLegend}>
          <View style={styles.legendDot} />
          <Text style={styles.legendText}>Reps</Text>
        </View>
      </View>

      <Svg
        width="100%"
        height={CHART_HEIGHT}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        accessibilityLabel="Bar chart showing repetitions for each day of this week"
      >
        {ticks.map((tick) => {
          const y = PLOT_TOP + plotHeight - (tick / maxValue) * plotHeight;
          return (
            <React.Fragment key={`tick-${tick}`}>
              <Line
                x1={PLOT_LEFT}
                x2={CHART_WIDTH - PLOT_RIGHT}
                y1={y}
                y2={y}
                stroke={COLORS.cardBorder}
                strokeWidth={1}
                strokeDasharray={tick === 0 ? undefined : "3 4"}
              />
              <SvgText
                x={PLOT_LEFT - 8}
                y={y + 3}
                fontSize={9}
                fill={COLORS.textMuted}
                textAnchor="end"
              >
                {tick}
              </SvgText>
            </React.Fragment>
          );
        })}

        {points.map((point, index) => {
          const centerX = PLOT_LEFT + slotWidth * index + slotWidth / 2;
          const barHeight =
            point.rep_count > 0
              ? Math.max(3, (point.rep_count / maxValue) * plotHeight)
              : 2;
          const barY = PLOT_TOP + plotHeight - barHeight;
          const isToday = point.date === today;
          const barFill = isToday
            ? COLORS.primaryOrange
            : COLORS.primaryOrangeLight;

          return (
            <React.Fragment key={point.date}>
              <Rect
                x={centerX - BAR_WIDTH / 2}
                y={PLOT_TOP}
                width={BAR_WIDTH}
                height={plotHeight}
                rx={BAR_WIDTH / 2}
                fill="rgba(255,255,255,0.035)"
              />
              <Rect
                x={centerX - BAR_WIDTH / 2}
                y={barY}
                width={BAR_WIDTH}
                height={barHeight}
                rx={BAR_WIDTH / 2}
                fill={barFill}
              />
              {point.rep_count > 0 ? (
                <SvgText
                  x={centerX}
                  y={Math.max(14, barY - 6)}
                  fontSize={10}
                  fontWeight="700"
                  fill={COLORS.textPrimary}
                  textAnchor="middle"
                >
                  {point.rep_count}
                </SvgText>
              ) : null}
              <SvgText
                x={centerX}
                y={CHART_HEIGHT - 9}
                fontSize={10}
                fill={isToday ? COLORS.primaryOrange : COLORS.textSecondary}
                fontWeight={isToday ? "700" : "500"}
                textAnchor="middle"
              >
                {formatDate(point.date, { weekday: "short" })}
              </SvgText>
            </React.Fragment>
          );
        })}
      </Svg>

      {!hasReps ? (
        <Text style={styles.chartEmptyText}>
          No saved repetitions this week yet. Complete a session to see your
          activity here.
        </Text>
      ) : null}
    </View>
  );
}

export default function ThisWeekSection() {
  const [summary, setSummary] = useState<WeeklyTrendSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useFocusEffect(
    useCallback(() => {
      let isCurrentRequest = true;

      const loadWeeklyTrend = async () => {
        setIsLoading(true);
        setErrorMessage(null);

        try {
          const response = await apiClient.get<unknown>(
            "/analytics/weekly-trend/",
          );
          const payload = response.data;

          if (!isWeeklyTrendSummary(payload)) {
            throw new Error(
              "The weekly trend response is missing valid daily activity data. Check the weekly analytics serializer and view.",
            );
          }

          if (!isCurrentRequest) return;

          setSummary(payload);

          if (__DEV__) {
            console.info("[ThisWeek] Weekly trend loaded", {
              url: response.config.url,
              week_start: payload.week_start,
              rep_count: payload.rep_count,
              session_count: payload.session_count,
              daily_activity: payload.daily_activity,
            });
          }
        } catch (error) {
          if (!isCurrentRequest) return;
          setErrorMessage(getErrorMessage(error));

          if (axios.isAxiosError(error)) {
            console.error("[ThisWeek] Weekly trend request failed", {
              url: error.config?.url,
              baseURL: error.config?.baseURL,
              status: error.response?.status,
              response: error.response?.data,
            });
          } else {
            console.error(
              "[ThisWeek] Weekly trend could not be rendered",
              error,
            );
          }
        } finally {
          if (isCurrentRequest) setIsLoading(false);
        }
      };

      void loadWeeklyTrend();

      return () => {
        isCurrentRequest = false;
      };
    }, [retryKey]),
  );

  const hasSummary = summary !== null;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.headerCopy}>
          <Text style={styles.title}>This Week</Text>
          <Text style={styles.subtitle}>
            {summary
              ? `Week of ${formatDate(summary.week_start, {
                  month: "short",
                  day: "numeric",
                })}`
              : "Your weekly workout activity"}
          </Text>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Refresh weekly activity"
          onPress={() => setRetryKey((value) => value + 1)}
          disabled={isLoading}
          style={({ pressed }) => [
            styles.refreshButton,
            (pressed || isLoading) && styles.refreshButtonMuted,
          ]}
        >
          <Text style={styles.refreshText}>
            {isLoading ? "Loading…" : "Refresh"}
          </Text>
        </Pressable>
      </View>

      {isLoading && !hasSummary ? (
        <View style={styles.statusRow}>
          <ActivityIndicator color={COLORS.primaryOrange} />
          <Text style={styles.statusText}>Loading weekly activity…</Text>
        </View>
      ) : null}

      {errorMessage && !hasSummary ? (
        <View style={styles.errorBlock}>
          <Text style={styles.errorText}>{errorMessage}</Text>
          <Pressable
            accessibilityRole="button"
            onPress={() => setRetryKey((value) => value + 1)}
            style={styles.retryButton}
          >
            <Text style={styles.retryButtonText}>Try again</Text>
          </Pressable>
        </View>
      ) : null}

      {summary ? (
        <>
          <View style={styles.metricsRow}>
            <View style={[styles.metricCard, styles.primaryMetricCard]}>
              <Text style={styles.metricValue}>
                {summary.rep_count.toLocaleString()}
              </Text>
              <Text style={styles.metricLabel}>Reps completed</Text>
            </View>
            <View style={styles.metricCard}>
              <Text style={styles.metricValue}>
                {summary.session_count.toLocaleString()}
              </Text>
              <Text style={styles.metricLabel}>Sessions</Text>
            </View>
          </View>

          <WeeklyActivityChart
            weekStart={summary.week_start}
            data={summary.daily_activity}
          />

          <View style={styles.previousWeekRow}>
            <View>
              <Text style={styles.previousWeekLabel}>Previous week</Text>
              <Text style={styles.previousWeekHint}>For comparison</Text>
            </View>
            <View style={styles.previousWeekTotals}>
              <Text style={styles.previousWeekValue}>
                {summary.previous_week_rep_count.toLocaleString()} reps
              </Text>
              <Text style={styles.previousWeekSessions}>
                {summary.previous_week_session_count.toLocaleString()} sessions
              </Text>
            </View>
          </View>

          {errorMessage ? (
            <Text style={styles.staleDataNote}>
              Refresh failed. Showing the last successfully loaded data.
            </Text>
          ) : null}

          {isLoading ? (
            <ActivityIndicator
              size="small"
              color={COLORS.primaryOrange}
              style={styles.refreshIndicator}
            />
          ) : null}
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.cardBg,
    borderColor: COLORS.cardBorder,
    borderWidth: 1,
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    marginBottom: SPACING.xl,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: SPACING.lg,
    gap: SPACING.md,
  },
  headerCopy: { flex: 1 },
  title: {
    color: COLORS.textPrimary,
    fontSize: 18,
    fontWeight: "700",
  },
  subtitle: {
    color: COLORS.textSecondary,
    fontSize: 12,
    marginTop: SPACING.xs,
  },
  refreshButton: {
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderRadius: RADIUS.full,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  refreshButtonMuted: { opacity: 0.55 },
  refreshText: {
    color: COLORS.primaryOrange,
    fontSize: 12,
    fontWeight: "700",
  },
  statusRow: {
    minHeight: 64,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: SPACING.sm,
  },
  statusText: { color: COLORS.textSecondary, fontSize: 13 },
  errorBlock: { gap: SPACING.md, paddingVertical: SPACING.sm },
  errorText: { color: COLORS.crimsonRed, fontSize: 13, lineHeight: 19 },
  retryButton: {
    alignSelf: "flex-start",
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderRadius: RADIUS.md,
    backgroundColor: COLORS.primaryOrangeGlow,
  },
  retryButtonText: {
    color: COLORS.primaryOrange,
    fontWeight: "700",
    fontSize: 12,
  },
  metricsRow: {
    flexDirection: "row",
    gap: SPACING.md,
    marginBottom: SPACING.lg,
  },
  metricCard: {
    flex: 1,
    minHeight: 86,
    justifyContent: "center",
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    backgroundColor: "rgba(255,255,255,0.025)",
  },
  primaryMetricCard: {
    borderColor: COLORS.primaryOrange,
    backgroundColor: COLORS.primaryOrangeGlow,
  },
  metricValue: {
    color: COLORS.textPrimary,
    fontSize: 26,
    fontWeight: "800",
    fontVariant: ["tabular-nums"],
  },
  metricLabel: {
    color: COLORS.textSecondary,
    fontSize: 12,
    fontWeight: "600",
    marginTop: SPACING.xs,
  },
  chartContainer: {
    borderTopWidth: 1,
    borderTopColor: COLORS.cardBorder,
    paddingTop: SPACING.md,
    marginBottom: SPACING.md,
  },
  chartHeadingRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: SPACING.xs,
    gap: SPACING.sm,
  },
  chartTitle: {
    color: COLORS.textPrimary,
    fontSize: 14,
    fontWeight: "700",
  },
  chartDescription: {
    color: COLORS.textMuted,
    fontSize: 10,
    marginTop: 3,
  },
  chartLegend: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 5,
    borderRadius: RADIUS.full,
    backgroundColor: "rgba(255,255,255,0.035)",
  },
  legendDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: COLORS.primaryOrange,
  },
  legendText: {
    color: COLORS.textSecondary,
    fontSize: 10,
    fontWeight: "600",
  },
  chartEmptyText: {
    color: COLORS.textMuted,
    fontSize: 12,
    lineHeight: 18,
    textAlign: "center",
    paddingHorizontal: SPACING.md,
    marginTop: SPACING.xs,
  },
  previousWeekRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: COLORS.cardBorder,
    paddingTop: SPACING.md,
    gap: SPACING.md,
  },
  previousWeekLabel: {
    color: COLORS.textSecondary,
    fontSize: 12,
    fontWeight: "600",
  },
  previousWeekHint: {
    color: COLORS.textMuted,
    fontSize: 10,
    marginTop: 3,
  },
  previousWeekTotals: { alignItems: "flex-end", gap: 3 },
  previousWeekValue: {
    color: COLORS.textPrimary,
    fontSize: 12,
    fontWeight: "700",
  },
  previousWeekSessions: {
    color: COLORS.textSecondary,
    fontSize: 11,
  },
  staleDataNote: {
    color: COLORS.warningYellow,
    fontSize: 12,
    marginTop: SPACING.sm,
  },
  refreshIndicator: {
    marginTop: SPACING.sm,
    alignSelf: "flex-end",
  },
});
