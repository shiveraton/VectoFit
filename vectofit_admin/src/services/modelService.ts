import client from "../config/client";

export type DeploymentStatus = "active" | "building" | "failed" | "inactive";

export type PredictionTarget = "binary_form" | "error_type" | "knee_alignment";

export type ModelCardCheckStatus = "pass" | "warn" | "fail";

export interface ModelCardCheck {
  code: string;
  label: string;
  status: ModelCardCheckStatus;
  detail: string;
  remediation: string | null;
}

export interface ModelCard {
  schema_version: string;
  status: "ready" | "warning" | "blocked";
  generated_from: {
    job_id: number;
    registry_entry_id: number;
    manifest_version: number | null;
    manifest_sha256: string | null;
  };
  activation: {
    allowed: boolean;
    blockers: ModelCardCheck[];
    warnings: ModelCardCheck[];
  };
  checks: ModelCardCheck[];
  summary: {
    total_checks: number;
    passed_checks: number;
    warning_checks: number;
    failed_checks: number;
  };
  class_mapping: Record<string, string>;
  target_names: string[];
  prediction_target: PredictionTarget;
  view_angle: "diagonal" | "frontal" | "sagittal" | "";
  feature_schema_version: string;
  evaluation_scope: string;
  held_out_test_count: number;
  data_provenance: {
    participant_count: number;
    label_origin_counts: Record<string, number>;
    split_counts: Record<string, number>;
  };
}

export interface PerClassMetric {
  index: number;
  label: string;
  support: number;
  predicted_count: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
}

export interface ModelRegistryRecord {
  id: number;
  name: string;
  version: string;
  training_job: number;
  algorithm: string;
  view_angle: "diagonal" | "frontal" | "sagittal" | "";
  prediction_target: PredictionTarget;
  feature_schema_version: string;
  metrics: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface ModelState {
  id: number;
  name: string;
  version: string;
  algorithm: string;
  view_angle: "diagonal" | "frontal" | "sagittal" | "";
  prediction_target: PredictionTarget;
  feature_schema_version: string;
  is_active: boolean;
  created_at: string;
  artifact_available: boolean;

  training: {
    job_id: number;
    status: string;
    view_angle: "diagonal" | "frontal" | "sagittal" | "";
    prediction_target: PredictionTarget;
    feature_schema_version: string;
    test_size: number;
    dataset_names: string[];
    sample_count: number;
    train_count: number;
    test_count: number;
    split_strategy: string;
    random_seed: number;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
  };

  features: {
    selected: string[];
    importances: Record<string, number>;
  };

  evaluation: {
    accuracy: number | null;
    balanced_accuracy: number | null;
    precision: number | null;
    recall: number | null;
    f1: number | null;
    confusion_matrix: number[][];
    class_mapping: Record<string, string>;
    target_names: string[];
    per_class: PerClassMetric[];
    overall_class_distribution: Record<string, number>;
    train_class_distribution: Record<string, number>;
    test_class_distribution: Record<string, number>;
    evaluation_scope: string;
    test_count: number;
  };

  feature_warnings: string[];
  training_manifest: Record<string, unknown>;
  model_card: ModelCard;
}

export const modelService = {
  async getModels(): Promise<ModelRegistryRecord[]> {
    const response =
      await client.get<ModelRegistryRecord[]>("/training/models/");

    return response.data;
  },

  async activateModel(id: number): Promise<ModelRegistryRecord> {
    const response = await client.post<ModelRegistryRecord>(
      `/training/models/${id}/activate/`,
    );
    return response.data;
  },

  async getModelState(id: number): Promise<ModelState> {
    const response = await client.get<ModelState>(
      `/training/models/${id}/state/`,
    );

    return response.data;
  },
};
