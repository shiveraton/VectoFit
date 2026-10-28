import client from "../config/client";
import type { ViewAngle } from "./datasetService";

export type PredictionTarget = "binary_form" | "error_type";

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
  random_seed: number;
  test_size: number;
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
    | "hip_angle"
    | "knee_angle"
    | "rom"
    | "asymmetry"
    | "trunk_angle"
    | "velocity";
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

export type Hyperparameters = Record<string, unknown>;

export interface WorkflowStep {
  number: string;
  title: string;
  subtitle: string;
  active?: boolean;
}
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
    test_size: number;
    random_seed: number;
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
        id: "rom",
        name: "ROM",
        selected: true,
      },
      {
        id: "asymmetry",
        name: "Asymmetry",
        selected: true,
      },
      {
        id: "trunk_angle",
        name: "Trunk Angle",
        selected: true,
      },
      {
        id: "knee_angle",
        name: "Knee Angle",
        selected: true,
      },
      {
        id: "hip_angle",
        name: "Hip Angle",
        selected: true,
      },
      {
        id: "velocity",
        name: "Velocity",
        selected: true,
      },
    ];
  },

  getAvailableAlgorithms(): AlgorithmOption[] {
    return [
      {
        id: "xgboost",
        code: "xgb",
        name: "XGBoost",
        description:
          "Gradient-boosted decision trees for squat movement classification.",
      },
    ];
  },

  getSplitStrategy(): SplitStrategyOption[] {
    return [
      {
        id: "group_by_participant",
        name: "Group by Participant",
        description:
          "Keeps repetitions from the same participant in a single split to prevent subject-level leakage.",
      },
    ];
  },

  getWorkflowStep(): WorkflowStep[] {
    return [
      {
        number: "01",
        title: "Configure",
        subtitle: "Dataset, task and features",
        active: true,
      },
      {
        number: "02",
        title: "Train",
        subtitle: "Fit the selected model",
      },
      {
        number: "03",
        title: "Evaluate",
        subtitle: "Measure model performance",
      },
      {
        number: "04",
        title: "Register",
        subtitle: "Save the trained model",
      },
    ];
  },
};