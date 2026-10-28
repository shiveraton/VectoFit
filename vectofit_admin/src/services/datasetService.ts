import client from "../config/client";

export interface CreateDatasetPayload {
  name: string;
  description?: string;
  participant: number | null;
  exercise_type: string;
  purpose: string;
  primary_target: string;
  secondary_target?: string;
  view_angle?: number | null;
  video_file: File | null;
}

export interface Participant {
  id: number;
  participant_code: string;
  created_at: string;
}

export type ViewAngle = "diagonal" | "frontal" | "sagittal";

export const VIEW_ANGLE_BY_ID: Record<number, ViewAngle> = {
  1: "diagonal",
  2: "frontal",
  3: "sagittal",
};

export interface Dataset {
  id: number;
  name: string;
  description: string;
  participant: number | null;
  view_angle: number | null;

  exercise_type: string;
  purpose: string;
  primary_target: string;
  secondary_target: string;

  created_at: string;
  updated_at: string;

  sample_count: number;
  labelled_sample_count: number;
  is_usable_for_training: boolean;

  status: DatasetStatus;
  error_message: string | null;

  video_file: string | null;
  video_url: string | null;
  video_count?: number;
  ready_video_count?: number;
  failed_video_count?: number;
}

export interface DatasetImportFile {
  archive_path: string;
  filename: string;
  participant_code: string;
  view_angle: ViewAngle;
  source_label: boolean;
  size_bytes: number;
}

export interface DatasetImportPreview {
  upload_token: string | null;
  file_count: number;
  participant_count: number;
  by_angle: Record<ViewAngle, number>;
  by_label: {
    good: number;
    bad: number;
  };
  files: DatasetImportFile[];
  warnings: string[];
  errors: string[];
  ignored_file_count: number;
}

export interface DatasetBulkImportPayload {
  upload_token: string;
  name: string;
  description?: string;
  exercise_type: string;
  purpose: string;
  primary_target: string;
  secondary_target?: string;
  files?: DatasetImportFile[];
}

export interface DatasetBulkImportResult {
  dataset: Dataset;
  imported_videos: number;
  queued_videos: number;
  queue_failures: Array<{
    video_id: number;
    error: string;
  }>;
}

export type DatasetStatus =
  | "PENDING"
  | "PROCESSING"
  | "READY"
  | "FAILED"
  | "PARTIAL";

export const datasetService = {
  async getDatasets(): Promise<Dataset[]> {
    const response = await client.get<Dataset[]>("/datasets/");
    return response.data;
  },

  async getDataset(id: number): Promise<Dataset> {
    const response = await client.get<Dataset>(`/datasets/${id}/`);
    return response.data;
  },

  async getParticipants(): Promise<Participant[]> {
    const response = await client.get<Participant[]>("/datasets/participant/");
    return response.data;
  },

  async createDatasetWithVideo(payload: FormData): Promise<Dataset> {
    const response = await client.post<Dataset>("/datasets/", payload, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  },

  async retryDataset(id: number): Promise<Dataset> {
    const response = await client.post<Dataset>(`/datasets/${id}/retry/`);

    return response.data;
  },

  async previewDatasetArchive(file: File): Promise<DatasetImportPreview> {
    const formData = new FormData();
    formData.append("zip_file", file);

    const response = await client.post<DatasetImportPreview>(
      "/datasets/import/preview/",
      formData,
    );

    return response.data;
  },

  async commitDatasetArchive(
    payload: DatasetBulkImportPayload,
  ): Promise<DatasetBulkImportResult> {
    const response = await client.post<DatasetBulkImportResult>(
      "/datasets/import/",
      payload,
    );

    return response.data;
  },
};
