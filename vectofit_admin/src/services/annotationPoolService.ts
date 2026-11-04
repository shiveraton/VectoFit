import client from "../config/client";

export type AnnotationJobStatus =
  | "NO_SAMPLES"
  | "QUEUED"
  | "IN_PROGRESS"
  | "COMPLETED";

export interface AnnotationPoolAnnotator {
  id: number | null;
  username: string;
}

export interface AnnotationPoolAnnotatorSummary {
  annotator: AnnotationPoolAnnotator | null;
  activity_count: number;
  last_activity_at: string;
}

export interface AnnotationPoolActivity {
  id: number;
  sample_id: number;
  annotator: AnnotationPoolAnnotator | null;
  created_at: string;
  has_annotation: boolean;
}

export interface AnnotationPoolJob {
  id: number;
  name: string;
  dataset_status: string;
  job_status: AnnotationJobStatus;
  sample_count: number;
  reviewed_count: number;
  pending_count: number;
  activity_count: number;
  created_at: string;
  updated_at: string;
  last_activity_at: string;
  annotators: AnnotationPoolAnnotatorSummary[];
  activity: AnnotationPoolActivity[];
}

export const annotationPoolService = {
  async getJobs(): Promise<AnnotationPoolJob[]> {
    const response = await client.get<AnnotationPoolJob[]>(
      "/datasets/annotation-pool/",
    );
    return response.data;
  },
};
