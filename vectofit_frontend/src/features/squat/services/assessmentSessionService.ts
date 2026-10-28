import apiClient from "../../../api/client";
import type {
  AssessmentViewAngle,
  SquatExerciseType,
} from "../../../navigation/types";
import type { RepAnalysisResult } from "../../assessment/services/sessionStructure";

type ExerciseVariantType = "BW" | "GOB" | "BAR";
type AssessmentStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

interface ExerciseVariant {
  id: number;
  name: string;
  variant_type: ExerciseVariantType;
  is_active: boolean;
}

interface ExerciseVariantListResponse {
  results?: ExerciseVariant[];
}

export interface AssessmentSessionDetail {
  id: number;
  exercise_variant: number;
  exercise_variant_name?: string;
  view_angle: AssessmentViewAngle | "";
  status: AssessmentStatus;
  error_message: string;
  reps: Array<{
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
  }>;
  rep_count: number;
}

const EXERCISE_VARIANT_TYPE: Record<SquatExerciseType, ExerciseVariantType> = {
  bodyweight_squat: "BW",
  goblet_squat: "GOB",
  barbell_squat: "BAR",
};

function getErrorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: unknown } }).response;
    const data = response?.data;
    if (typeof data === "object" && data !== null) {
      const detail = "detail" in data ? data.detail : undefined;
      if (typeof detail === "string") return detail;
      return JSON.stringify(data);
    }
  }

  return error instanceof Error ? error.message : String(error);
}

export async function uploadSquatAssessmentVideo(
  videoPath: string,
  exercise: SquatExerciseType,
  viewAngle: AssessmentViewAngle,
): Promise<AssessmentSessionDetail> {
  if (!videoPath.trim()) {
    throw new Error("No recorded video path was provided.");
  }

  const variantsResponse = await apiClient.get<
    ExerciseVariant[] | ExerciseVariantListResponse
  >("/exercises/variants/");
  const variantData = variantsResponse.data;
  const variants: ExerciseVariant[] = Array.isArray(variantData)
    ? (variantData as ExerciseVariant[])
    : ((variantData as ExerciseVariantListResponse).results ?? []);
  const expectedType = EXERCISE_VARIANT_TYPE[exercise];
  const variant = variants.find(
    (item) => item.variant_type === expectedType && item.is_active,
  );

  if (!variant) {
    throw new Error(
      `No active exercise variant found for ${exercise} (variant type ${expectedType}).`,
    );
  }

  const uri = videoPath.startsWith("file://")
    ? videoPath
    : `file://${videoPath}`;
  const filename = videoPath.split("/").pop() || `squat-${Date.now()}.mp4`;
  const formData = new FormData();

  formData.append("exercise_variant", String(variant.id));
  formData.append("view_angle", viewAngle);
  formData.append("video_file", {
    uri,
    name: filename.endsWith(".mp4") ? filename : `${filename}.mp4`,
    type: "video/mp4",
  } as unknown as Blob);

  const createResponse = await apiClient.post<{ id: number }>(
    "/assessments/sessions/",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    },
  );

  if (!createResponse.data?.id) {
    throw new Error(
      "The server did not return the created assessment session ID.",
    );
  }

  const detailResponse = await apiClient.get<AssessmentSessionDetail>(
    `/assessments/sessions/${createResponse.data.id}/`,
    { params: { include: "reps" } },
  );
  const session = detailResponse.data;

  if (session.status === "FAILED") {
    throw new Error(
      `Video was uploaded, but rep processing failed: ${session.error_message || "No error details were returned."}`,
    );
  }

  console.info("[RepCount] Session detail received", {
    sessionId: session.id,
    apiRepCount: session.rep_count,
    repsLength: session.reps?.length ?? 0,
    repNumbers: session.reps?.map((rep) => rep.rep_number) ?? [],
  });

  return session;
}

export { getErrorMessage as getAssessmentUploadErrorMessage };
