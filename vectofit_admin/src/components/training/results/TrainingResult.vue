<script setup lang="ts">
import { computed } from "vue";

import ConfusionMatrix from "./ConfusionMatrix.vue";
import FeatureImportance from "./FeatureImportance.vue";
import TrainingMetricInfo from "./TrainingMetricInfo.vue";

interface TrainingMetrics {
  accuracy?: number;
  balanced_accuracy?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  confusion_matrix?: unknown;
  target_names?: unknown;
  class_mapping?: unknown;
  prediction_target?: string;
  feature_importances?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface TrainingResultJob {
  id: string | number;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | string;
  sample_count?: number | null;
  train_count?: number | null;
  test_count?: number | null;
  test_size?: number;
  completed_at?: string | null;
  started_at?: string | null;
  error_message?: string | null;
  metrics?: TrainingMetrics | null;
  hyperparameters?: Record<string, unknown> | null;
  feature_selection?: string[] | null;
  random_seed?: number | null;
  split_strategy?: string | null;
  dataset_names?: string[] | null;
  view_angle?: string | null;
  prediction_target?: string | null;
}

const props = defineProps<{
  job: TrainingResultJob | null;
}>();

const formatMetric = (value: unknown) => {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return `${(value * 100).toFixed(1)}%`;
};

const formatDate = (value: string | null | undefined) => {
  if (!value) return "--";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";

  return date.toLocaleString("en-PH", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

const formatValue = (value: unknown) => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Number.isInteger(value)
      ? String(value)
      : value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  }

  if (typeof value === "string" || typeof value === "boolean") {
    return String(value);
  }

  return "--";
};

const featureImportance = computed(() => {
  const raw = props.job?.metrics?.feature_importances;
  if (!raw || typeof raw !== "object") return [];

  return Object.entries(raw)
    .filter(([, value]) => typeof value === "number" && Number.isFinite(value))
    .map(([name, value]) => ({ name, value: Number(value) }))
    .sort((a, b) => b.value - a.value);
});

const confusionMatrix = computed(
  () => props.job?.metrics?.confusion_matrix ?? null,
);

const targetNames = computed(() => {
  const raw = props.job?.metrics?.target_names;

  if (Array.isArray(raw)) {
    const names = raw.filter(
      (value): value is string =>
        typeof value === "string" && value.trim() !== "",
    );
    if (names.length) return names;
  }

  const mapping = props.job?.metrics?.class_mapping;
  if (mapping && typeof mapping === "object") {
    return Object.keys(mapping as Record<string, unknown>)
      .sort((a, b) => Number(a) - Number(b))
      .map((key) => String((mapping as Record<string, unknown>)[key]));
  }

  return [];
});

const metricCopy = {
    balancedAccuracyDescription:
      "Balanced accuracy gives equal importance to good and bad knee-alignment labels.",
    precisionTitle: "Macro Precision",
    precisionQuestion:
      "How precise are predictions across good and bad knee-alignment labels?",
    precisionDescription:
      "Macro precision is the unweighted mean precision across the good and bad classes.",
    precisionInterpretation:
      "Each knee-alignment class contributes equally, so poor precision on either label lowers this score.",
    recallTitle: "Macro Recall",
    recallQuestion: "How well does the model identify both knee-alignment labels?",
    recallDescription:
      "Macro recall is the unweighted mean recall for good and bad knee-alignment labels.",
    recallInterpretation:
      "Each knee-alignment class contributes equally, so poor recall on either label lowers this score.",
    f1Title: "Macro F1",
  };

const usedParameters = computed(() => {
  const parameters: Array<{ label: string; value: string }> = [];
  const raw = props.job?.hyperparameters;

  if (raw && typeof raw === "object") {
    Object.entries(raw).forEach(([key, value]) => {
      if (
        typeof value === "number" ||
        typeof value === "string" ||
        typeof value === "boolean"
      ) {
        parameters.push({ label: key, value: formatValue(value) });
      }
    });
  }

  if (typeof props.job?.test_size === "number") {
    parameters.push({ label: "Requested test fraction", value: formatMetric(props.job.test_size) });
  }
  if (typeof props.job?.random_seed === "number") {
    parameters.push({
      label: "random_seed",
      value: String(props.job.random_seed),
    });
  }

  return parameters;
});

const featureLabels: Record<string, string> = {
  fppa_l_bottom: "Left FPPA at bottom",
  fppa_r_bottom: "Right FPPA at bottom",
  fppa_l_peak: "Left peak FPPA",
  fppa_r_peak: "Right peak FPPA",
  asym_bottom: "Bottom bilateral asymmetry",
  asym_peak: "Peak bilateral asymmetry",
};

const featureList = computed(() =>
  (props.job?.feature_selection ?? []).map(
    (feature) => featureLabels[feature] ?? feature,
  ),
);

const resultInterpretation = computed(() => {
  const f1 = props.job?.metrics?.f1;
  const balancedAccuracy = props.job?.metrics?.balanced_accuracy;

  if (typeof f1 !== "number" || typeof balancedAccuracy !== "number") {
    return "Review the available metrics, test-set counts, and confusion matrix before considering activation.";
  }

  return `The held-out test repetitions produced a macro F1 of ${formatMetric(f1)} and balanced accuracy of ${formatMetric(balancedAccuracy)}. Review both together with the confusion matrix before considering the trained FPPA model for activation.`;
});
</script>

<template>
  <div v-if="!job" class="result-empty">
    <div class="result-empty-icon">M1</div>
    <h3>No FPPA training result yet</h3>
    <p>
      Configure an experiment above and start training to generate held-out
      metrics, feature importance, and classification results.
    </p>
  </div>

  <div v-else class="result-content">
    <div class="result-overview">
      <div class="overview-item">
        <span>Training Job</span>
        <strong>#{{ job.id }}</strong>
      </div>
      <div class="overview-item">
        <span>Samples</span>
        <strong>{{ job.sample_count ?? "--" }}</strong>
      </div>
      <div class="overview-item">
        <span>Train / Test repetitions</span>
        <strong
          >{{ job.train_count ?? "--" }} / {{ job.test_count ?? "--" }}</strong
        >
      </div>
      <div class="overview-item">
        <span>Completed</span>
        <strong>{{ formatDate(job.completed_at) }}</strong>
      </div>
    </div>

    <div
      v-if="job.status === 'RUNNING' || job.status === 'PENDING'"
      class="run-state running-state"
    >
      <span class="state-icon" aria-hidden="true">…</span>
      <div>
        <strong>Training is in progress</strong>
        <p>
          The configuration is active. Final evaluation metrics will appear here
          once the job completes.
        </p>
      </div>
    </div>

    <div v-else-if="job.status === 'FAILED'" class="run-state failed-state">
      <span class="state-icon" aria-hidden="true">!</span>
      <div>
        <strong>Training failed</strong>
        <p>
          {{
            job.error_message ||
            "No error message was returned by the training service."
          }}
        </p>
      </div>
    </div>

    <template v-else-if="job.status === 'COMPLETED'">
      <p>
        Evaluation: participant-grouped holdout. These scores are separate from the pilot LOPO comparison.
        Train / test participants: {{ job.metrics?.train_participant_count ?? "--" }} /
        {{ job.metrics?.test_participant_count ?? "--" }}.
      </p>
      <div class="metrics-grid">
        <TrainingMetricInfo
          title="Accuracy"
          :value="formatMetric(job.metrics?.accuracy)"
          question="How often did the model make the correct overall decision?"
          description="Accuracy is the proportion of held-out test repetitions classified correctly."
          interpretation="High accuracy is useful, but it can hide class imbalance, so inspect balanced accuracy and the confusion matrix too."
        />
        <TrainingMetricInfo
          title="Balanced Accuracy"
          :value="formatMetric(job.metrics?.balanced_accuracy)"
          question="Did the model perform reasonably across every class?"
          description="Balanced accuracy averages recall across target classes so each class contributes equally."
          :interpretation="metricCopy.balancedAccuracyDescription"
        />
        <TrainingMetricInfo
          :title="metricCopy.precisionTitle"
          :value="formatMetric(job.metrics?.precision)"
          :question="metricCopy.precisionQuestion"
          :description="metricCopy.precisionDescription"
          :interpretation="metricCopy.precisionInterpretation"
        />
        <TrainingMetricInfo
          :title="metricCopy.recallTitle"
          :value="formatMetric(job.metrics?.recall)"
          :question="metricCopy.recallQuestion"
          :description="metricCopy.recallDescription"
          :interpretation="metricCopy.recallInterpretation"
        />
        <TrainingMetricInfo
          :title="metricCopy.f1Title"
          variant="primary"
          :value="formatMetric(job.metrics?.f1)"
          question="How well does the model balance precision and recall?"
          description="F1 combines precision and recall into a single score using their harmonic mean."
          interpretation="Use F1 as a useful comparison metric, but do not interpret it without the test-set composition and confusion matrix."
        />
      </div>

      <div class="result-interpretation">
        <div class="interpretation-icon">?</div>
        <div>
          <strong>What does this result mean?</strong>
          <p>{{ resultInterpretation }}</p>
        </div>
      </div>

      <div class="result-grid">
        <FeatureImportance :values="featureImportance" />
        <ConfusionMatrix
          :matrix="confusionMatrix"
          :labels="targetNames"
        />
      </div>

      <div class="parameter-summary">
        <header class="subsection-header">
          <div>
            <h3>Experiment Configuration Used</h3>
            <p>The configuration stored with this training run.</p>
          </div>
        </header>

        <div class="used-parameters">
          <div
            v-for="parameter in usedParameters"
            :key="parameter.label"
            class="used-parameter"
          >
            <span>{{ parameter.label }}</span>
            <strong>{{ parameter.value }}</strong>
          </div>
          <div class="used-parameter">
            <span>view_angle</span>
            <strong>{{ job.view_angle || "--" }}</strong>
          </div>
          <div class="used-parameter">
            <span>split_strategy</span>
            <strong>{{ job.split_strategy || "group_by_participant" }}</strong>
          </div>
        </div>

        <div class="feature-summary">
          <span>Features</span>
          <strong>{{
            featureList.length ? featureList.join(" · ") : "Not recorded"
          }}</strong>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.result-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 54px 22px 58px;
  text-align: center;
}

.result-empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  margin-bottom: 15px;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 800;
}

.result-empty h3 {
  margin: 0;
  color: var(--vf-dark);
  font-size: 15px;
}

.result-empty p {
  max-width: 430px;
  margin: 7px 0 0;
  color: var(--vf-light-muted);
  font-size: 12px;
  line-height: 1.6;
}

.result-content {
  padding: 22px;
}

.result-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.overview-item {
  padding: 11px 12px;
  background: #fafafa;
  border: 1px solid var(--vf-border-light);
  border-radius: 8px;
}

.overview-item span,
.overview-item strong {
  display: block;
}

.overview-item span {
  color: var(--vf-light-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.overview-item strong {
  margin-top: 5px;
  color: var(--vf-text);
  font-size: 12px;
}

.run-state {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 16px;
  padding: 13px;
  border-radius: 8px;
  border: 1px solid;
}

.running-state {
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border-color: #fed7aa;
}

.failed-state {
  color: #991b1b;
  background: var(--vf-red-soft);
  border-color: #fecaca;
}

.state-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 7px;
  background: #ffffff;
  font-size: 13px;
  font-weight: 800;
}

.run-state strong,
.run-state p {
  display: block;
}

.run-state strong {
  color: var(--vf-text);
  font-size: 12px;
}

.run-state p {
  margin: 4px 0 0;
  color: inherit;
  font-size: 11px;
  line-height: 1.5;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 9px;
  margin-top: 16px;
}

.result-interpretation {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 13px;
  padding: 12px;
  background: #fffaf6;
  border: 1px solid #fed7aa;
  border-radius: 8px;
}

.interpretation-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 800;
}

.result-interpretation strong,
.result-interpretation p {
  display: block;
}

.result-interpretation strong {
  color: var(--vf-text);
  font-size: 12px;
}

.result-interpretation p {
  margin: 4px 0 0;
  color: var(--vf-muted);
  font-size: 11px;
  line-height: 1.55;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 13px;
}

.parameter-summary {
  margin-top: 13px;
  padding: 16px;
  background: #fcfcfc;
  border: 1px solid var(--vf-border-light);
  border-radius: 10px;
}

.subsection-header h3 {
  margin: 0;
  color: var(--vf-text);
  font-size: 13px;
}

.subsection-header p {
  margin: 4px 0 0;
  color: var(--vf-light-muted);
  font-size: 11px;
}

.used-parameters {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.used-parameter {
  padding: 9px;
  background: #ffffff;
  border: 1px solid var(--vf-border-light);
  border-radius: 7px;
}

.used-parameter span,
.used-parameter strong {
  display: block;
}

.used-parameter span {
  color: var(--vf-light-muted);
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
}

.used-parameter strong {
  margin-top: 4px;
  overflow: hidden;
  color: var(--vf-text);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feature-summary {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr);
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--vf-border-light);
  font-size: 11px;
}

.feature-summary span {
  color: var(--vf-light-muted);
}

.feature-summary strong {
  color: var(--vf-text);
  font-weight: 600;
  line-height: 1.5;
}

@media (max-width: 1100px) {
  .metrics-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .used-parameters {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .result-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .result-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .metrics-grid,
  .used-parameters {
    grid-template-columns: 1fr;
  }

  .feature-summary {
    grid-template-columns: 1fr;
  }
}
</style>
