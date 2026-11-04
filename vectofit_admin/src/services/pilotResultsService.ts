import client from "../config/client";

export interface PilotParticipantResult {
  participant: string;
  macro_f1: number;
  sample_count: number;
}

export interface PilotMetricResult {
  macro_f1: number;
  confusion_matrix: number[][];
  per_participant: PilotParticipantResult[];
}

export interface PilotResults {
  label: string;
  feature_schema_version: string;
  M0_features: string[];
  M1_features: string[];
  M0: PilotMetricResult;
  M1: PilotMetricResult;
  delta_macro_f1: number;
  delta_macro_f1_bootstrap_95: {
    lower: number;
    upper: number;
  };
  threshold_rule_baseline: {
    rule: string;
    primary: PilotMetricResult & {
      label: string;
      cutoff_degrees: { valgus: number; varus: number };
    };
    sensitivity: Array<
      PilotMetricResult & {
        label: string;
        cutoff_degrees: { valgus: number; varus: number };
      }
    >;
  };
}

export const pilotResultsService = {
  async getResults(): Promise<PilotResults> {
    const response = await client.get<PilotResults>("/training/pilot-results/");
    return response.data;
  },
};
