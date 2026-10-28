import client from "../config/client";

export type DeploymentStatus = "active" | "building" | "failed" | "inactive";

export interface ModelRegistryRecord {
  id: number;
  name: string;
  version: string;
  training_job: number;
  algorithm: string;
  view_angle: "diagonal" | "frontal" | "sagittal" | "";
  prediction_target: "binary_form" | "error_type";
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
  prediction_target: "binary_form" | "error_type";
  feature_schema_version: string;
  is_active: boolean;
  created_at: string;
  artifact_available: boolean;

  training: {
    job_id: number;
    status: string;
    view_angle: "diagonal" | "frontal" | "sagittal" | "";
    prediction_target: "binary_form" | "error_type";
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
    overall_class_distribution: Record<string, number>;
    train_class_distribution: Record<string, number>;
    test_class_distribution: Record<string, number>;
  };

  feature_warnings: string[];
  training_manifest: Record<string, unknown>;
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
