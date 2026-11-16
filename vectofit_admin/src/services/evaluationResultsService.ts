import client from "../config/client";

export interface EvaluationParticipantResult {
  participant: string;
  macro_f1: number;
  sample_count: number;
}

export interface EvaluationMetricResult {
  macro_f1: number;
  confusion_matrix: number[][];
  per_participant: EvaluationParticipantResult[];
  oof_predictions?: Array<{
    participant: string;
    label: number;
    prediction: number;
  }>;
}

export interface EvaluationResults {
  label: string;
  feature_schema_version: string;
  M0_features: string[];
  M1_features: string[];
  M0: EvaluationMetricResult;
  M1: EvaluationMetricResult;
  delta_macro_f1: number;
  delta_macro_f1_bootstrap_95: {
    lower: number;
    upper: number;
  };
  threshold_rule_baseline: {
    rule: string;
    primary: EvaluationMetricResult & {
      label: string;
      cutoff_degrees: { valgus: number; varus: number };
    };
    sensitivity: Array<
      EvaluationMetricResult & {
        label: string;
        cutoff_degrees: { valgus: number; varus: number };
      }
    >;
  };
}

export const evaluationResultsService = {
  async getResults(): Promise<EvaluationResults> {
    const response = await client.get<EvaluationResults>("/training/pilot-results/");
    return response.data;
  },
};
