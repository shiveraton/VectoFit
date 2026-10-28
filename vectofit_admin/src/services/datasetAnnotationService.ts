import client from "../config/client";

export type CriterionKey =
  | "depth"
  | "knee"
  | "trunk"
  | "symmetry"
  | "foot"
  | "completion";

export type CriterionValue = boolean | null;

export interface AnnotationCriteria {
  depth: CriterionValue;
  knee: CriterionValue;
  trunk: CriterionValue;
  symmetry: CriterionValue;
  foot: CriterionValue;
  completion: CriterionValue;
}

export interface RepAssessment {
  id: number;
  rep_number: number;
  start_frame: number | null;
  end_frame: number | null;
  classification: string;
}

export interface DatasetSample {
  id: number;
  dataset: number;
  rep_assessment: RepAssessment;
  is_correct: boolean | null;
  error_label: string;
  annotator: number | null;
  annotated_at: string | null;
  created_at: string;
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

export interface SaveAnnotationPayload {
  is_correct: boolean | null;
  error_label: string;
}

export const datasetAnnotationService = {
  async getSession(datasetId: number): Promise<AnnotationSession> {
    const response = await client.get<AnnotationSession>(
      `/datasets/${datasetId}/annotation/`,
    );

    return response.data;
  },

  async save(
    sampleId: number,
    payload: SaveAnnotationPayload,
  ): Promise<DatasetSample> {
    const response = await client.patch<DatasetSample>(
      `/datasets/dataset-samples/${sampleId}/`,
      payload,
    );

    return response.data;
  },

  async clear(sampleId: number): Promise<DatasetSample> {
    const response = await client.patch<DatasetSample>(
      `/datasets/dataset-samples/${sampleId}/`,
      {
        is_correct: null,
        error_label: "",
      },
    );

    return response.data;
  },
};
