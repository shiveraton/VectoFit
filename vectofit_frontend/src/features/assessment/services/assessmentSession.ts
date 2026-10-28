import apiClient from "../../../api/client";

export type AssessmentStatus =
  | "PENDING"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";

export interface AssessmentSessionSummary {
  id: number;
  exercise_variant: number | string;
  exercise_variant_name?: string;
  status: AssessmentStatus | string;
  created_at: string;
  processed_at: string | null;
  rep_count: number;
  error_message?: string;
}

export type AssessmentSession = AssessmentSessionSummary;

export interface RepAnalysisResult {
  metrics?: Record<string, unknown>;
  classifications?: Record<string, unknown>;
  feedback?: Array<{ metric?: string; message?: string }>;
  [key: string]: unknown;
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
}

export interface AssessmentSessionDetail extends AssessmentSessionSummary {
  body_profile: number | null;
  video_file: string;
  error_message: string;
  reps: AssessmentRep[];
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
  );
  return response.data;
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
