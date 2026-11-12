import axios from "axios";
import client from "../config/client";
import { initializeCsrf, publicClient } from "../config/publicAuth";
const isPublic = import.meta.env.MODE === "public";

export type KneeAlignmentGrade =
  | "aligned"
  | "borderline"
  | "deviated"
  | "unassessable";

export type KneeDeviationDirection = "valgus" | "varus" | "none" | "uncertain";

export type SymmetryObservation =
  | "symmetric"
  | "asymmetric"
  | "uncertain"
  | "not_recorded";

export type TargetLabel = "good" | "bad" | "borderline" | "unassessable";

export interface KneeSideAnnotation {
  grade: KneeAlignmentGrade | null;
  direction: KneeDeviationDirection | null;
}

export interface KneeAnnotation {
  left: KneeSideAnnotation;
  right: KneeSideAnnotation;
  symmetry_observation: SymmetryObservation;
  notes: string;
}

export interface RepAssessment {
  id: number;
  rep_number: number;
  start_frame: number | null;
  end_frame: number | null;
  classification: string;
}

export interface DatasetVideoPlayback {
  id: number;
  video_url: string | null;
  participant_code: string;
  view_angle_name: string;
  source_label?: boolean | null;
  source_path?: string;
  requires_manual_review?: boolean;
}

export interface DatasetSample {
  id: number;
  dataset: number;
  dataset_video: DatasetVideoPlayback | number | null;
  video_fps?: number | null;
  is_manually_annotated?: boolean;
  rep_assessment: RepAssessment;

  is_correct: boolean | null;
  error_label: string;
  annotator: number | null;
  annotated_at: string | null;
  created_at: string;

  knee_annotation?: KneeAnnotation | null;
  target_label?: TargetLabel | null;
}

export interface AnnotationSession {
  dataset: {
    id: number;
    name: string;
    exercise_type: string;
    view_angle: number | null;
    video_url: string | null;
    sample_count: number;
    labelled_sample_count: number;
    is_usable_for_training: boolean;
    status: string;
  };
  fps: number;
  samples: DatasetSample[];
}

export interface DatasetSamplePlaybackFields {
  dataset_video: DatasetVideoPlayback | null;
  video_fps: number | null;
}

export interface SaveAnnotationPayload {
  knee_annotation: KneeAnnotation;
}

export const emptyKneeAnnotation = (): KneeAnnotation => ({
  left: { grade: null, direction: null },
  right: { grade: null, direction: null },
  symmetry_observation: "not_recorded",
  notes: "",
});

export const datasetAnnotationService = {
  async getSession(datasetId: number): Promise<AnnotationSession> {
    const response = await client.get<AnnotationSession>(
      isPublic
        ? `/annotator/datasets/${datasetId}/session/`
        : `/datasets/${datasetId}/annotation/`,
    );
    return response.data;
  },

  async save(
    sampleId: number,
    payload: SaveAnnotationPayload,
  ): Promise<DatasetSample> {
    if (isPublic) {
      await initializeCsrf();
      const { data } = await publicClient.patch<DatasetSample>(
        `samples/${sampleId}/rating/`,
        payload,
      );
      return data;
    }
    const response = await client.patch<DatasetSample>(
      `/datasets/dataset-samples/${sampleId}/`,
      payload,
    );
    return response.data;
  },

  async clear(sampleId: number): Promise<DatasetSample> {
    if (isPublic) {
      await initializeCsrf();
      const { data } = await publicClient.patch<DatasetSample>(
        `samples/${sampleId}/rating/`,
        { knee_annotation: null },
      );
      return data;
    }
    const response = await client.patch<DatasetSample>(
      `/datasets/dataset-samples/${sampleId}/`,
      { knee_annotation: null },
    );
    return response.data;
  },
};

export function annotationRequestError(
  error: unknown,
  fallback: string,
): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : fallback;
  }
  if (!error.response) {
    return `${fallback} Check your connection and try again.`;
  }
  const { status, data } = error.response;
  if (data && typeof data === "object") {
    const messages = Object.values(data).flatMap((value) =>
      typeof value === "string"
        ? [value]
        : Array.isArray(value)
          ? value.filter((item): item is string => typeof item === "string")
          : [],
    );
    if (messages.length) return messages.join(" ");
  }
  if (status === 401)
    return "Your session expired. Sign in again before saving.";
  if (status === 403)
    return "Saving was denied. Reload the page and check your annotation access.";
  if (status === 404)
    return "This repetition is no longer available for your account. Reload the dataset.";
  return `${fallback} The server returned HTTP ${status}.`;
}
