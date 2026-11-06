import apiClient from "../../../api/client";

export type AssessmentStatus =
  | "PENDING"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";

export type FindingCode =
  | "VALGUS_LEFT"
  | "VALGUS_RIGHT"
  | "VARUS";

export type FindingSeverity = "minor" | "major";

export type FindingPattern =
  | "constant"
  | "worsening"
  | "improving"
  | "isolated";

export type SessionVerdictStatus = "clean" | "minor_issues" | "needs_work";

export interface SessionReportMetric {
  key: "depth_deg" | "trunk_lean_deg" | "asymmetry_pct";
  label: string;
  unit: string;
  target: number;
  mean: number;
  worst: {
    rep: number;
    value: number;
  };
  passed_reps: number;
}

export interface SessionReportFinding {
  code: FindingCode;
  title: string;
  summary: string;
  cue: string;
  severity: FindingSeverity;
  affected_reps: number[];
  worst_excess: number;
  pattern: FindingPattern;
}

export interface SessionReportRep {
  n: number;
  depth_deg: number | null;
  trunk_lean_deg: number | null;
  asymmetry_pct: number | null;
  flags: FindingCode[];
}

export interface SessionReportScores {
  jaa: number;
  rom: number;
  bad: number;
  kvt: number;
  hybrid: number;
}

export interface SessionReport {
  schema_version: 1;
  verdict: {
    status: SessionVerdictStatus;
    headline: string;
    clean_reps: number;
    total_reps: number;
  };
  metrics: SessionReportMetric[];
  findings: SessionReportFinding[];
  trends: {
    depth_drift_deg: number | null;
    velocity_loss_pct: number | null;
  };
  reps: SessionReportRep[];
  coverage: {
    not_evaluated: string[];
  };
  scores: SessionReportScores | null;
}

export interface AssessmentSessionSummary {
  id: number;
  exercise_variant: number | string;
  exercise_variant_name?: string;
  status: AssessmentStatus | string;
  created_at: string;
  processed_at: string | null;
  rep_count: number;
  error_message?: string;
  report: SessionReport | null;
}

export type AssessmentSession = AssessmentSessionSummary;

export interface RepAnalysisResult {
  metrics?: Record<string, unknown>;
  classifications?: Record<string, unknown>;
  feedback?: Array<{ metric?: string; message?: string }>;
  model_prediction?: ModelPrediction;
  fppa?: FppaAnalysis;
  [key: string]: unknown;
}

export interface FppaKneeResult {
  peak_degrees: number;
  direction: "inward" | "outward" | null;
  state: "aligned" | "deviation";
}

export interface FppaAnalysis {
  status: "assessed" | "not_assessed";
  reason?: string;
  cutoff_degrees?: number;
  knees?: {
    left: FppaKneeResult;
    right: FppaKneeResult;
  };
}

export type ModelPredictionStatus = "assessed" | "not_assessed";

export interface ModelPrediction {
  status: ModelPredictionStatus;
  reason?: string;
  detail?: string;
  model_id?: number;
  model_name?: string;
  model_version?: string;
  view_angle?: "diagonal" | "frontal" | "sagittal";
  prediction_target?: "knee_alignment" | "binary_form" | "error_type" | string;
  feature_schema_version?: string;
  predicted_class?: string;
  probability?: number | null;
  class_probabilities?: Record<string, number>;
  is_correct?: boolean;
}

export interface AssessmentRep {
  id: number;
  rep_number: number;
  jaa_score: number | null;
  rom_score: number | null;
  bad_score: number | null;
  kvt_score: number | null;
  hybrid_score: number | null;
  classification: string;
  analysis_result: RepAnalysisResult | null;
  start_frame: number | null;
  end_frame: number | null;
  key_frame_index: number | null;
  snapshot_landmarks?: Record<string, { x: number; y: number }> | null;
  snapshot_frame_width?: number | null;
  snapshot_frame_height?: number | null;
  snapshot_reference_available?: boolean;
}

export interface AssessmentSessionDetail extends AssessmentSessionSummary {
  body_profile: number | null;
  video_file: string;
  error_message: string;
  view_angle?: "diagonal" | "frontal" | "sagittal" | "";
  reps?: AssessmentRep[];
}

interface PaginatedResponse<T> {
  results?: T[];
}

function unwrapList<T>(data: T[] | PaginatedResponse<T>): T[] {
  return Array.isArray(data) ? data : (data.results ?? []);
}

export async function getAssessmentSessions(): Promise<
  AssessmentSessionSummary[]
> {
  const response = await apiClient.get<
    AssessmentSessionSummary[] | PaginatedResponse<AssessmentSessionSummary>
  >("/assessments/sessions/");

  return unwrapList(response.data);
}

export async function getAssessmentSession(
  sessionId: number,
): Promise<AssessmentSessionDetail> {
  const response = await apiClient.get<AssessmentSessionDetail>(
    `/assessments/sessions/${sessionId}/`,
    { params: { include: "reps" } },
  );

  return response.data;
}

export function getAssessmentRepSnapshotUrl(repId: number): string {
  return apiClient.getUri({ url: `/assessments/reps/${repId}/snapshot/` });
}

export function getAssessmentErrorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: unknown } }).response;
    const data = response?.data;

    if (typeof data === "object" && data !== null) {
      const detail = "detail" in data ? data.detail : undefined;
      if (typeof detail === "string") return detail;
      return JSON.stringify(data);
    }
  }

  return error instanceof Error
    ? error.message
    : "An unexpected error occurred.";
}
