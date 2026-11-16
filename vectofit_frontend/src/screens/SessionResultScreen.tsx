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
function fppaResult(rep: AssessmentRep) {
  return rep.analysis_result?.fppa;
}
function getModelResult(rep: AssessmentRep) {
  const prediction = rep.analysis_result?.model_prediction;
  const predictedClass = prediction?.predicted_class;
  const probability = prediction?.probability;

  if (
    prediction?.status !== "assessed" ||
    prediction.prediction_target !== "knee_alignment" ||
    (prediction.view_angle && prediction.view_angle !== "frontal") ||
    (predictedClass !== "good" && predictedClass !== "bad") ||
    typeof probability !== "number" ||
    !Number.isFinite(probability) ||
    probability < 0 ||
    probability > 1
  ) {
    return null;
  }

  return {
    predictedClass,
    label: predictedClass === "good" ? "Good" : "Bad",
    confidence: Math.round(probability * 100),
  };
}

function modelLabel(rep: AssessmentRep): string {
  return getModelResult(rep)?.label ?? "Unavailable";
}

function getFppaResult(rep: AssessmentRep) {
  const result = fppaResult(rep);
  const knees = result?.knees;
  if (
    result?.status !== "assessed" ||
    !knees ||
    ![knees.left, knees.right].every(
      (knee) =>
        knee &&
        Number.isFinite(knee.peak_degrees) &&
        (knee.state === "aligned" || knee.state === "deviation"),
    ) ||
    typeof result.cutoff_degrees !== "number" ||
    !Number.isFinite(result.cutoff_degrees) ||
    result.cutoff_degrees < 0
  ) {
    return null;
  }

  return {
    knees,
    cutoff: result.cutoff_degrees,
    hasDeviation:
      knees.left.state === "deviation" || knees.right.state === "deviation",
  };
}

function fppaUnavailableText(rep: AssessmentRep): string {
  const reason = fppaResult(rep)?.reason;
  if (reason === "invalid_bottom_frame")
    return "Bottom position was not clear. Re-record from a stable frontal view.";
  if (reason === "insufficient_valid_frames")
    return "Too many pose frames were unclear. Re-record with your full body visible.";
  if (reason === "shorter_than_filter_window")
    return "The repetition was too short to assess. Re-record at a steady pace.";
  if (reason === "view_not_supported")
    return "FPPA assessment requires a frontal camera view.";
  return "This repetition could not be assessed. Please re-record.";
}
function findingForRep(
  findings: SessionReportFinding[],
  rep: AssessmentRep,
): SessionReportFinding | undefined {
  const measurement = getFppaResult(rep);
  if (!measurement?.hasDeviation) return undefined;

  const { left, right } = measurement.knees;
  const supportedFindings = {
    VALGUS_LEFT: left.state === "deviation" && left.direction === "inward",
    VALGUS_RIGHT: right.state === "deviation" && right.direction === "inward",
    VARUS:
      (left.state === "deviation" && left.direction === "outward") ||
      (right.state === "deviation" && right.direction === "outward"),
  };
  return findings
    .filter(
      (finding) =>
        finding.affected_reps.includes(rep.rep_number) &&
        supportedFindings[finding.code],
    )
    .sort(
      (a, b) =>
        (a.severity === "major" ? -1 : 1) - (b.severity === "major" ? -1 : 1),
    )[0];
}

function getRepCoaching(
  rep: AssessmentRep,
  finding?: SessionReportFinding,
) {
  const model = getModelResult(rep);
  const measurement = getFppaResult(rep);
  if (!measurement) {
    return {
      label: "Recording guidance",
      cue: fppaUnavailableText(rep),
    };
  }
  if (model && (model.predictedClass === "bad") !== measurement.hasDeviation) {
    return {
      label: "Review conflicting results",
      cue: "Review the FPPA measurements and snapshot, then repeat the recording from a stable frontal view with both knees visible.",
    };
  }
  if (measurement.hasDeviation && finding?.cue) {
    return { label: "FPPA-based coaching", cue: finding.cue };
  }
  return {
    label: "Recording guidance",
    cue: "Keep the camera frontal and repeat the movement with steady control.",
  };
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
        Observed hip-to-ankle line and knee marker show FPPA
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
  const modelResult = getModelResult(rep);
  const fppaMeasurement = getFppaResult(rep);
  const coaching = getRepCoaching(rep, finding);
  const resultsDisagree =
    modelResult &&
    fppaMeasurement &&
    (modelResult.predictedClass === "bad") !== fppaMeasurement.hasDeviation;
  return (
    <View style={styles.repCard}>
      <View style={styles.repHeader}>
        <Text style={styles.repTitle}>Rep {rep.rep_number}</Text>
        <Text style={styles.statusPill}>
          Model knee alignment · {modelLabel(rep)}
        </Text>
      </View>
      <RepSnapshot rep={rep} />
      <Text style={styles.issueLabel}>FPPA measurements</Text>
      {fppaMeasurement ? (
        <>
          <Text style={styles.cardText}>
            FPPA threshold result · {fppaMeasurement.hasDeviation ? "Deviation" : "Aligned"}
          </Text>
          <Text style={styles.mutedText}>
            Deviation cutoff · absolute peak angle greater than {fppaMeasurement.cutoff}°
          </Text>
          {(["left", "right"] as const).map((side) => {
            const knee = fppaMeasurement.knees[side];
            return (
              <Text key={side} style={styles.cardText}>
                {side === "left" ? "Left" : "Right"} knee peak FPPA · {knee.peak_degrees.toFixed(1)}°
                {" · "}{knee.state === "deviation" ? "Deviation" : "Within cutoff"}
                {knee.direction === "inward" || knee.direction === "outward"
                  ? ` (${knee.direction})`
                  : ""}
              </Text>
            );
          })}
          <Text style={styles.mutedText}>
            Positive angles indicate inward alignment; negative angles indicate outward alignment.
          </Text>
        </>
      ) : (
        <Text style={styles.cardText}>FPPA measurements unavailable. {fppaUnavailableText(rep)}</Text>
      )}
      {resultsDisagree ? (
        <Text style={styles.noticeText}>
          Results disagree. The model predicts {modelResult.label.toLowerCase()} knee alignment,
          while FPPA indicates {fppaMeasurement.hasDeviation ? "a deviation" : "alignment within the cutoff"}.
        </Text>
      ) : null}
      <Text style={styles.issueLabel}>FPPA findings</Text>
      <Text style={styles.cardText}>
        {(fppaMeasurement && finding?.summary) ||
          (fppaMeasurement
            ? fppaMeasurement.hasDeviation
              ? "FPPA measured a knee deviation beyond the cutoff."
              : "Both knees were within the predeclared FPPA cutoff."
            : fppaUnavailableText(rep))}
      </Text>
      <Text style={styles.issueLabel}>{coaching.label}</Text>
      <Text style={styles.cueText}>{coaching.cue}</Text>
      <View style={styles.cardFooter}>
        {modelResult ? (
          <>
            <Text style={styles.mutedText}>
              Model knee alignment: {modelResult.label}
            </Text>
            <Text style={styles.mutedText}>
              Model confidence: {modelResult.confidence}%
            </Text>
          </>
        ) : (
          <Text style={styles.mutedText}>
            Model knee alignment assessment unavailable
          </Text>
        )}
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
  const modelResults = reps.map(getModelResult);
  const goodReps = reps.filter(
    (rep) => getModelResult(rep)?.predictedClass === "good",
  );
  const goodCount = goodReps.length;
  const badCount = modelResults.filter(
    (result) => result?.predictedClass === "bad",
  ).length;
  const assessedCount = goodCount + badCount;
  const unavailableCount = reps.length - assessedCount;
  if (reps.length === 0)
    return (
      <View style={styles.notice}>
        <Text style={styles.noticeTitle}>Assessment unavailable</Text>
        <Text style={styles.noticeText}>
          0 assessed | 0 unassessed
          {"\n"}
          No repetition results were returned for this session.
        </Text>
      </View>
    );
  return (
    <>
      <View style={styles.summaryCard}>
        <Text style={styles.summaryHeadline}>
          {assessedCount === 0
            ? "Assessment unavailable"
            : badCount > 0
              ? "The model flagged knee alignment concerns."
              : "The model assessed knee alignment as good for assessed reps."}
        </Text>
        <Text style={styles.summaryText}>
          {assessedCount} assessed | {unavailableCount} unassessed
          {"\n"}
          {goodCount} good | {badCount} bad
          {"\n"}
          Model knee alignment assessment across {reps.length} repetitions.
        </Text>
      </View>
      <Text style={styles.sectionTitle}>Choose a repetition</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.repSelector}
      >
        {reps.map((rep, index) => {
          const modelResult = getModelResult(rep);
          const statusStyle = !modelResult
            ? styles.repChipUnavailable
            : modelResult.predictedClass === "bad"
              ? styles.repChipBad
              : styles.repChipGood;
          return (
            <Pressable
              key={rep.id}
              accessibilityRole="button"
              accessibilityLabel={`Repetition ${rep.rep_number}, model knee alignment ${modelLabel(rep)}`}
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
          reps[Math.min(selectedIndex, reps.length - 1)],
        )}
      />
      {goodReps.length
        ? goodReps.map((rep) => (
            <View key={rep.id} style={styles.goodRepRow}>
              <Text style={styles.repTitle}>Rep {rep.rep_number}</Text>
              <Text style={styles.mutedText}>
                Model knee alignment · {modelLabel(rep)}
              </Text>
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
