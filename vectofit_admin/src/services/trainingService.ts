import client from "../config/client";
import type { ViewAngle } from "./datasetService";

export type PredictionTarget = "binary_form" | "error_type" | "knee_alignment";

export type TrainingJobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface TrainingJob {
  id: number;
  dataset_ids: number[];
  dataset_names: string[];
  algorithm: string;
  view_angle: ViewAngle | "";
  prediction_target: PredictionTarget;
  feature_schema_version: string;
  training_manifest_summary?: Record<string, unknown>;
  feature_selection: string[];
  hyperparameters: Record<string, unknown>;
  split_strategy: string;
  status: TrainingJobStatus;
  error_message: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  sample_count: number;
  train_count: number;
  test_count: number;
  metrics: Record<string, unknown>;
  feature_warnings: string[];
  has_artifact: boolean;
  artifact_url: string | null;
}

export interface FeatureOption {
  id:
    | "fppa_l_bottom"
    | "fppa_r_bottom"
    | "fppa_l_peak"
    | "fppa_r_peak"
    | "asym_bottom"
    | "asym_peak";
  name: string;
  selected: boolean;
}

export interface AlgorithmOption {
  id: "xgboost";
  code: string;
  name: string;
  description: string;
}

export interface SplitStrategyOption {
  id: string;
  name: string;
  description: string;
}

export interface WorkflowStep {
  number: string;
  title: string;
  subtitle: string;
  active?: boolean;
}

export type Hyperparameters = Record<string, unknown>;

export const trainingService = {
  async getTrainingJobs(): Promise<TrainingJob[]> {
    const response = await client.get<TrainingJob[]>("/training/jobs/");
    return response.data;
  },

  async startTraining(payload: {
    dataset_ids: number[];
    algorithm: string;
    view_angle: ViewAngle;
    prediction_target: PredictionTarget;
    feature_selection: string[];
    hyperparameters: Record<string, unknown>;
  }): Promise<TrainingJob> {
    const response = await client.post<TrainingJob>(
      "/training/jobs/create/",
      payload,
    );

    return response.data;
  },

  getAvailableFeatures(): FeatureOption[] {
    return [
      {
        id: "fppa_l_bottom",
        name: "Left FPPA at squat bottom",
        selected: true,
      },
      {
        id: "fppa_r_bottom",
        name: "Right FPPA at squat bottom",
        selected: true,
      },
      {
        id: "fppa_l_peak",
        name: "Left peak FPPA",
        selected: true,
      },
      {
        id: "fppa_r_peak",
        name: "Right peak FPPA",
        selected: true,
      },
      {
        id: "asym_bottom",
        name: "Bottom bilateral asymmetry",
        selected: true,
      },
      {
        id: "asym_peak",
        name: "Peak bilateral asymmetry",
        selected: true,
      },
    ];
  },

  getAvailableAlgorithms(): AlgorithmOption[] {
    return [
      {
        id: "xgboost",
        code: "xgb",
        name: "XGBoost M1",
        description:
          "Predicts human-reviewed good/bad knee-alignment labels from FPPA v2 features.",
      },
    ];
  },

  getSplitStrategy(): SplitStrategyOption[] {
    return [
      {
        id: "leave_one_participant_out",
        name: "Leave one participant out (LOPO)",
        description:
          "Holds out each participant once and combines their out-of-fold predictions.",
      },
    ];
  },

};
