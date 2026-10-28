import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { InsightsStackParamList } from "../navigation/insightsTypes";
import useAuthStore from "../stores/useAuthStore";
import {
  getAssessmentErrorMessage,
  getAssessmentRepSnapshotUrl,
  getAssessmentSession,
  type AssessmentRep,
  type AssessmentSessionDetail,
  type ModelPrediction,
  type SessionReportFinding,
} from "../features/assessment/services/sessionStructure";
import { COLORS } from "../styles/designTokens";
import styles from "../styles/SessionResultScreenStyles";

type Props = NativeStackScreenProps<InsightsStackParamList, "SessionResult">;

function formatDate(value?: string | null): string {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
}
function binaryPrediction(rep: AssessmentRep): ModelPrediction | undefined {
  const prediction = rep.analysis_result?.model_prediction;
  return prediction?.prediction_target === "binary_form"
    ? prediction
    : undefined;
}
function isConfirmedBad(rep: AssessmentRep): boolean {
  const prediction = binaryPrediction(rep);
  const value = prediction?.predicted_class?.trim().toLowerCase();
  return (
    prediction?.status === "assessed" &&
    prediction.is_correct === false &&
    (value === "bad" || value === "bad_form")
  );
}
function predictionLabel(prediction?: ModelPrediction): string {
  if (!prediction || prediction.status !== "assessed")
    return "Model unavailable";
  const value = prediction.predicted_class?.trim().toLowerCase();
  if (value === "good" || value === "good_form") return "Good Form";
  if (value === "bad" || value === "bad_form") return "Needs Improvement";
  return "Unsupported result";
}
function unavailableText(prediction?: ModelPrediction): string {
  if (prediction?.detail) return prediction.detail;
  if (prediction?.reason === "no_active_model")
    return "No active model was available for this camera angle.";
  if (prediction?.reason === "feature_extraction_failed")
    return "There was not enough usable movement data for inference.";
  return "Model inference was unavailable for this repetition.";
}
function findingForRep(
  findings: SessionReportFinding[],
  repNumber: number,
): SessionReportFinding | undefined {
  return findings
    .filter((finding) => finding.affected_reps.includes(repNumber))
    .sort(
      (a, b) =>
        (a.severity === "major" ? -1 : 1) - (b.severity === "major" ? -1 : 1),
    )[0];
}

function RepSnapshot({ rep }: { rep: AssessmentRep }) {
  const token = useAuthStore((state) => state.token);
  const [failed, setFailed] = useState(false);
  return (
    <View
      style={[
        styles.snapshotFrame,
        rep.snapshot_frame_width && rep.snapshot_frame_height
          ? {
              aspectRatio: rep.snapshot_frame_width / rep.snapshot_frame_height,
            }
          : undefined,
      ]}
    >
      {failed ? (
        <Text style={styles.snapshotFallback}>Snapshot unavailable</Text>
      ) : (
        <Image
          source={{
            uri: getAssessmentRepSnapshotUrl(rep.id),
            headers: token ? { Authorization: `Token ${token}` } : undefined,
          }}
          style={styles.snapshotImage}
          resizeMode="contain"
          onError={() => setFailed(true)}
        />
      )}
      <Text style={styles.overlayLegend}>
        Red: observed posture
        {rep.snapshot_reference_available
          ? " · Green: reference"
          : " · No reference pose available"}
      </Text>
    </View>
  );
}
function RepCoachingCard({
  rep,
  finding,
}: {
  rep: AssessmentRep;
  finding?: SessionReportFinding;
}) {
  const prediction = binaryPrediction(rep);
  const confidence =
    prediction?.status === "assessed" &&
    typeof prediction.probability === "number" &&
    Number.isFinite(prediction.probability)
      ? `Model estimate · ${Math.round(prediction.probability * 100)}%`
      : null;
  return (
    <View style={styles.repCard}>
      <View style={styles.repHeader}>
        <Text style={styles.repTitle}>Rep {rep.rep_number}</Text>
        <Text style={styles.statusPill}>{predictionLabel(prediction)}</Text>
      </View>
      <RepSnapshot rep={rep} />
      <Text style={styles.issueLabel}>What we saw</Text>
      <Text style={styles.cardText}>
        {finding?.summary ??
          "This repetition was flagged, but a specific correction could not be isolated."}
      </Text>
      <Text style={styles.issueLabel}>Try this next</Text>
      <Text style={styles.cueText}>
        {finding?.cue ??
          "Repeat the movement with steady control and check your alignment before the next rep."}
      </Text>
      <View style={styles.cardFooter}>
        {confidence ? <Text style={styles.mutedText}>{confidence}</Text> : null}
      </View>
    </View>
  );
}
function ProcessingNotice({
  session,
  onRefresh,
}: {
  session: AssessmentSessionDetail;
  onRefresh: () => void;
}) {
  if (session.status === "COMPLETED") return null;
  const failed = session.status === "FAILED";
  return (
    <View
      style={[
        styles.notice,
        { borderColor: failed ? COLORS.crimsonRed : COLORS.warningYellow },
      ]}
    >
      <Text style={styles.noticeTitle}>
        {failed ? "Assessment failed" : "Assessment is still processing"}
      </Text>
      <Text style={styles.noticeText}>
        {failed
          ? session.error_message || "The assessment could not be completed."
          : "Refresh this result later to retrieve its saved coaching feedback."}
      </Text>
      {!failed ? (
        <Pressable style={styles.actionButton} onPress={onRefresh}>
          <Text style={styles.actionButtonText}>Refresh session</Text>
        </Pressable>
      ) : null}
    </View>
  );
}
function CoachingContent({ session }: { session: AssessmentSessionDetail }) {
  const report = session.report;
  const reps = session.reps ?? [];
  const findings = report?.findings ?? [];
  const [selectedIndex, setSelectedIndex] = useState(0);
  const goodReps: AssessmentRep[] = [];
  const [showGood, setShowGood] = useState(false);
  const assessedBadCount = reps.filter(isConfirmedBad).length;
  if (reps.length === 0)
    return (
      <View style={styles.notice}>
        <Text style={styles.noticeTitle}>No repetition results</Text>
        <Text style={styles.noticeText}>
          No repetition results were returned for this session.
        </Text>
      </View>
    );
  return (
    <>
      <View style={styles.summaryCard}>
        <Text style={styles.summaryHeadline}>
          {assessedBadCount
            ? "A few reps need attention."
            : "Reps looked good."}
        </Text>
        <Text style={styles.summaryText}>
          {assessedBadCount} of {reps.length} repetitions were flagged by the
          binary form model. Unassessed predictions are not counted as bad form.
        </Text>
      </View>
      <Text style={styles.sectionTitle}>Choose a repetition</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.repSelector}
      >
        {reps.map((rep, index) => {
          const prediction = binaryPrediction(rep);
          const statusStyle =
            prediction?.status !== "assessed"
              ? styles.repChipUnavailable
              : isConfirmedBad(rep) || findingForRep(findings, rep.rep_number)
                ? styles.repChipBad
                : styles.repChipGood;
          return (
            <Pressable
              key={rep.id}
              accessibilityRole="button"
              accessibilityLabel={`Repetition ${rep.rep_number}, ${predictionLabel(prediction)}`}
              style={[
                styles.repChip,
                statusStyle,
                index === selectedIndex && styles.repChipSelected,
              ]}
              onPress={() => setSelectedIndex(index)}
            >
              <Text style={styles.repChipText}>{rep.rep_number}</Text>
            </Pressable>
          );
        })}
      </ScrollView>

      <RepCoachingCard
        rep={reps[Math.min(selectedIndex, reps.length - 1)]}
        finding={findingForRep(
          findings,
          reps[Math.min(selectedIndex, reps.length - 1)].rep_number,
        )}
      />
      {/*
      <Pressable
        style={styles.goodToggle}
        onPress={() => setShowGood((current) => !current)}
      >
        <Text style={styles.goodToggleText}>
          {showGood ? "Hide" : "Reps that looked good"} · {goodReps.length}
        </Text>
        <Text style={styles.goodToggleIcon}>{showGood ? "⌃" : "⌄"}</Text>
      </Pressable> */}
      {showGood
        ? goodReps.map((rep) => (
            <View key={rep.id} style={styles.goodRepRow}>
              <Text style={styles.repTitle}>Rep {rep.rep_number}</Text>
              <Text style={styles.mutedText}>
                {predictionLabel(binaryPrediction(rep))}
              </Text>
              {binaryPrediction(rep)?.status !== "assessed" ? (
                <Text style={styles.mutedText}>
                  {unavailableText(binaryPrediction(rep))}
                </Text>
              ) : null}
            </View>
          ))
        : null}
    </>
  );
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
      setSession(await getAssessmentSession(sessionId));
    } catch (loadError) {
      setError(getAssessmentErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);
  useEffect(() => {
    void loadSession();
  }, [loadSession]);
  if (loading)
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.centerState}>
          <ActivityIndicator size="large" color={COLORS.primaryOrange} />
          <Text style={styles.stateTitle}>Loading session results</Text>
        </View>
      </SafeAreaView>
    );
  if (error || !session)
    return (
      <SafeAreaView style={styles.safeArea}>
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
  const exerciseName =
    session.exercise_variant_name?.trim() ||
    `Exercise variant #${session.exercise_variant}`;
  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Pressable
            onPress={() => navigation.goBack()}
            style={styles.backButton}
          >
            <Text style={styles.backButtonText}>‹</Text>
          </Pressable>
          <View style={styles.headerText}>
            <Text style={styles.eyebrow}>SESSION COACHING</Text>
            <Text style={styles.title}>{exerciseName}</Text>
          </View>
        </View>
        <View style={styles.metaLine}>
          <Text style={styles.dateText}>{formatDate(session.created_at)}</Text>
          <Text style={styles.dateText}>
            {session.reps?.length ?? session.rep_count ?? 0} reps
          </Text>
        </View>
        <ProcessingNotice
          session={session}
          onRefresh={() => void loadSession()}
        />
        {session.status === "COMPLETED" ? (
          <CoachingContent session={session} />
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
