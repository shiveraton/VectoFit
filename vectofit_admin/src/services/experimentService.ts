import client from "../config/client";

export interface ReadinessParticipant {
  group: string;
  code: string;
  good: number;
  bad: number;
  human_labelled: number;
}

export interface ReadinessReport {
  ok: boolean;
  reason: string;
  view_angle: string;
  n_reps: number;
  mixed_pipeline: boolean;
  pipeline_hash_count: number;
  exclusion_counts: Record<string, number>;
  lopo: { viable: boolean; folds: number; reason: string };
  participants: ReadinessParticipant[];
}

export interface ClassMetrics { precision: number; recall: number; f1: number }
export interface PooledMetrics {
  n_reps: number; n_bad: number; macro_f1: number; balanced_accuracy: number;
  bad: ClassMetrics; good: ClassMetrics;
}
export interface BootstrapDelta {
  mode: string; n_resamples: number; n_valid: number; point_delta: number;
  delta_ci: [number, number]; ci_level: number;
  share_delta_gt_0: number; share_delta_lt_0: number; n_participants: number;
}
export interface Jackknife {
  full_delta: number; without_participant: Record<string, number>;
  min: number; max: number; sign_flips: string[];
}
export interface ParticipantRow {
  participant: string; n_reps: number; n_bad: number; a_correct: number; b_correct: number;
}
export interface RuleResult {
  metrics: PooledMetrics; fold_thresholds: Record<string, number>;
  M0_minus_rule: BootstrapDelta; M1_minus_rule: BootstrapDelta;
}
export interface ComparisonBlock {
  models: { M0: PooledMetrics; M1: PooledMetrics };
  delta_macro_f1_M1_minus_M0: {
    bootstrap: BootstrapDelta; jackknife: Jackknife; per_participant: ParticipantRow[];
  };
  rule_baseline: Record<string, RuleResult>;
  lopo: { n_folds: number; skipped: unknown[]; evaluated_samples: number; unevaluated_samples: number };
}
export interface ExperimentResults {
  experiment_id: string; scope: string; demo: boolean;
  label_semantics: string; decision_rule: string; feature_schema_version: string;
  features: { M0: string[]; M1: string[] };
  hyperparameters_shared: Record<string, unknown>;
  seed: number; n_reps: number; n_participants: number;
  participants: Record<string, Record<string, number>>;
  main: ComparisonBlock; sensitivity: Record<string, ComparisonBlock>;
}
export interface ExperimentResultsResponse {
  available: boolean; bundle: string;
  results?: ExperimentResults; provenance?: Record<string, unknown> | null;
  participant_codes?: Record<string, string>;
}


export const experimentService = {
  async getReadiness(
    datasetIds: number[],
    viewAngle = "frontal",
  ): Promise<ReadinessReport> {
    const response = await client.get<ReadinessReport>(
      "/training/experiments/readiness/",
      { params: { dataset_ids: datasetIds.join(","), view_angle: viewAngle } },
    );
    return response.data;
  },
  async getResults(bundle: "main" | "demo"): Promise<ExperimentResultsResponse> {
    const response = await client.get<ExperimentResultsResponse>(
      "/training/experiments/results/", { params: { bundle } });
    return response.data;
  },
};
