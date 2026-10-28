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

export interface AngleTrainingStats {
  sample_count: number;
  labelled_sample_count: number;
  good_count: number;
  bad_count: number;
  error_type_sample_count: number;
  error_label_counts: Record<string, number>;
  participant_count: number;
  video_count: number;
}

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

  participant_count?: number;
  view_angles?: ViewAngle[];
  angle_training_stats?: Partial<Record<ViewAngle, AngleTrainingStats>>;

  review_policy?: "source_labels" | "all_videos" | "subset";
  review_selected_sample_count?: number;
  human_reviewed_sample_count?: number;
  pending_review_sample_count?: number;
  inherited_labelled_sample_count?: number;
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
  expires_at: number;
  manifest: DatasetImportManifest;
}

export interface DatasetImportManifest {
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isViewAngle(value: unknown): value is ViewAngle {
  return value === "diagonal" || value === "frontal" || value === "sagittal";
}

function isDatasetImportPreview(value: unknown): value is DatasetImportPreview {
  if (!isRecord(value)) {
    return false;
  }

  if (
    !(typeof value.upload_token === "string" || value.upload_token === null) ||
    !isNumber(value.expires_at) ||
    !isRecord(value.manifest)
  ) {
    return false;
  }

  const manifest = value.manifest;

  if (
    !isNumber(manifest.file_count) ||
    !isNumber(manifest.participant_count) ||
    !isNumber(manifest.ignored_file_count) ||
    !isRecord(manifest.by_label) ||
    !isRecord(manifest.by_angle)
  ) {
    return false;
  }

  const byLabel = manifest.by_label;
  const byAngle = manifest.by_angle;

  if (
    !isNumber(byLabel.good) ||
    !isNumber(byLabel.bad) ||
    !isNumber(byAngle.diagonal) ||
    !isNumber(byAngle.frontal) ||
    !isNumber(byAngle.sagittal)
  ) {
    return false;
  }

  if (
    !Array.isArray(manifest.files) ||
    !manifest.files.every(
      (file: unknown) =>
        isRecord(file) &&
        typeof file.archive_path === "string" &&
        typeof file.filename === "string" &&
        typeof file.participant_code === "string" &&
        isViewAngle(file.view_angle) &&
        typeof file.source_label == "boolean" &&
        isNumber(file.size_bytes),
    )
  ) {
    return false;
  }

  if (
    !Array.isArray(manifest.warnings) ||
    !manifest.warnings.every(
      (warning: unknown) => typeof warning === "string",
    ) ||
    !Array.isArray(manifest.errors) ||
    !manifest.errors.every((error: unknown) => typeof error === "string")
  ) {
    return false;
  }

  return true;
}

export type DatasetReviewPolicy = "source" | "all" | "subset";

export type DatasetSelectionMethod = "stratified" | "manual";

export interface DatasetBulkImportPayload {
  upload_token: string | null;
  name: string;
  description?: string;
  exercise_type: string;
  purpose: string;
  primary_target: string;
  secondary_target?: string;
  review_policy: DatasetReviewPolicy;
  selection_method: DatasetSelectionMethod;
  review_count?: number;
  random_seed?: number;
  selected_video_paths?: string[];
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
    const response = await client.post<Dataset>("/datasets/", payload);
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

    if (!isDatasetImportPreview(response.data)) {
      throw new Error(
        "The server returned an invalid archive preview response.",
      );
    }

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