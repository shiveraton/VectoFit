<script setup lang="ts">
import { computed } from "vue";
import type { ModelState } from "../../services/modelService";

const props = defineProps<{
  evaluation: ModelState["evaluation"];
}>();

const metricLabels: Record<string, string> = {
  accuracy: "Accuracy",
  balanced_accuracy: "Balanced Accuracy",
  precision: "Precision",
  recall: "Recall",
  f1: "F1 Score",
};

const metricValue = (key: string) => {
  const value = props.evaluation[key as keyof ModelState["evaluation"]];

  return typeof value === "number" ? value : null;
};

const formatMetric = (value: number | null) =>
  value == null ? "—" : `${(value * 100).toFixed(1)}%`;

const classLabels = computed(() => {
  const mapping = props.evaluation.class_mapping ?? {};
  const matrix = props.evaluation.confusion_matrix ?? [];
  const size = Array.isArray(matrix) ? matrix.length : 0;

  return Array.from(
    { length: size },
    (_, index) => mapping[String(index)] ?? `Class ${index}`,
  );
});

const confusionMatrix = computed(() => {
  const matrix = props.evaluation.confusion_matrix;

  if (!Array.isArray(matrix) || matrix.length === 0) return null;
  if (!matrix.every((row) => Array.isArray(row) && row.length === matrix.length)) {
    return null;
  }

  return matrix;
});

const distributionRows = computed(() => {
  const overall = props.evaluation.overall_class_distribution ?? {};
  const test = props.evaluation.test_class_distribution ?? {};
  const mapping = props.evaluation.class_mapping ?? {};
  const mappingKeys = Object.keys(mapping).sort((a, b) => Number(a) - Number(b));

  if (mappingKeys.length) {
    return mappingKeys.map((key) => {
      const label = mapping[key];

      return {
        key,
        label,
        overall: overall[label] ?? overall[key] ?? "—",
        test: test[label] ?? test[key] ?? "—",
      };
    });
  }

  const keys = Array.from(
    new Set([...Object.keys(overall), ...Object.keys(test)]),
  ).sort((a, b) => a.localeCompare(b));

  return keys.map((key) => ({
    key,
    label: key,
    overall: overall[key] ?? "—",
    test: test[key] ?? "—",
  }));
});
</script>

<template>
  <div class="evaluation-body">
    <div class="metric-grid">
      <div
        v-for="key in Object.keys(metricLabels)"
        :key="key"
        class="metric-item"
      >
        <span class="metric-label">
          {{ metricLabels[key] }}
        </span>

        <strong>
          {{ formatMetric(metricValue(key)) }}
        </strong>
      </div>
    </div>

    <div class="evaluation-bottom">
      <div class="matrix-wrap">
        <div class="subheading">Confusion matrix</div>

        <p class="helper">Held-out classification results.</p>

        <div
          v-if="confusionMatrix"
          class="matrix"
          :style="{
            gridTemplateColumns: `92px repeat(${classLabels.length}, minmax(0, 1fr))`,
          }"
        >
          <div class="matrix-corner">Actual ↓ / Pred. →</div>

          <div
            v-for="(label, index) in classLabels"
            :key="`predicted-${index}`"
            class="matrix-axis"
          >
            {{ label }}
          </div>

          <template
            v-for="(row, rowIndex) in confusionMatrix"
            :key="`actual-${rowIndex}`"
          >
            <div class="matrix-axis row-axis">
              {{ classLabels[rowIndex] ?? `Class ${rowIndex}` }}
            </div>
            <div
              v-for="(value, colIndex) in row"
              :key="`cell-${rowIndex}-${colIndex}`"
              class="matrix-cell"
            >
              {{ value }}
            </div>
          </template>
        </div>

        <div v-else class="matrix-empty">
          No square confusion matrix is available for this model.
        </div>
      </div>

      <div class="distribution-wrap">
        <div class="subheading">Class distribution</div>

        <p class="helper">Label counts retained with the training run.</p>

        <div v-if="distributionRows.length" class="distribution-grid">
          <div
            v-for="entry in distributionRows"
            :key="entry.key"
            class="distribution-card"
          >
            <span>{{ entry.label }}</span>
            <div class="distribution-values">
              <small>Overall</small>
              <strong>{{ entry.overall }}</strong>
              <small>Test</small>
              <strong>{{ entry.test }}</strong>
            </div>
          </div>
        </div>

        <p v-else class="helper">No class distribution was recorded.</p>
      </div>
    </div>

    <div v-if="evaluation.per_class?.length" class="per-class-wrap">
      <div class="subheading">Per-class performance</div>

      <p class="helper">
        Precision, recall, and F1 derived from the held-out confusion matrix.
        Support is the number of actual test samples for each class.
      </p>

      <div class="per-class-scroll">
        <div class="per-class-table">
          <div class="per-class-row per-class-header">
            <span>Class</span>
            <span>Support</span>
            <span>Predicted</span>
            <span>Precision</span>
            <span>Recall</span>
            <span>F1</span>
          </div>

          <div
            v-for="row in evaluation.per_class"
            :key="row.index"
            class="per-class-row"
          >
            <strong>{{ row.label }}</strong>
            <span>{{ row.support }}</span>
            <span>{{ row.predicted_count }}</span>
            <span>{{ formatMetric(row.precision) }}</span>
            <span>{{ formatMetric(row.recall) }}</span>
            <span>{{ formatMetric(row.f1) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.evaluation-body {
  padding: 24px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  border: 1px solid var(--vf-border-light);
  border-radius: 10px;
  overflow: hidden;
}

.metric-item {
  padding: 15px 16px;
  background: #fff;
}

.metric-item + .metric-item {
  border-left: 1px solid var(--vf-border-light);
}

.metric-label {
  display: block;
  margin-bottom: 7px;
  color: var(--vf-muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.metric-item strong {
  color: var(--vf-dark);
  font-size: 19px;
  font-variant-numeric: tabular-nums;
}

.evaluation-bottom {
  display: grid;
  grid-template-columns: 0.85fr 1.15fr;
  gap: 24px;
  margin-top: 24px;
}

.subheading {
  color: var(--vf-dark);
  font-size: 13px;
  font-weight: 700;
}

.helper {
  margin: 5px 0 14px;
  color: var(--vf-muted);
  font-size: 13px;
}

.matrix {
  display: grid;
  grid-template-columns: 92px 1fr 1fr;
  max-width: 560px;
  border: 1px solid var(--vf-border-light);
  border-radius: 10px;
  overflow: hidden;
}

.matrix > * {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50px;
  padding: 6px;
  text-align: center;
  overflow-wrap: anywhere;
}

.matrix-empty {
  max-width: 360px;
  padding: 18px;
  border: 1px dashed var(--vf-border-light);
  border-radius: 10px;
  color: var(--vf-muted);
  font-size: 12px;
  line-height: 1.6;
}

.matrix-axis,
.matrix-corner {
  background: #fafafa;
  color: var(--vf-muted);
  font-size: 12px;
  font-weight: 700;
}

.row-axis {
  justify-content: flex-start;
  padding-left: 12px;
}

.matrix-cell {
  border-top: 1px solid var(--vf-border-light);
  border-left: 1px solid var(--vf-border-light);
  color: var(--vf-dark);
  font-size: 15px;
  font-weight: 700;
}

.distribution-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.distribution-card {
  padding: 12px;
  border: 1px solid var(--vf-border-light);
  border-radius: 9px;
  background: #fafafa;
}

.distribution-card > span {
  display: block;
  overflow-wrap: anywhere;
  color: var(--vf-dark);
  font-size: 12px;
  font-weight: 700;
}

.distribution-values {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 4px 10px;
  margin-top: 7px;
}

.distribution-values small {
  color: var(--vf-muted);
  font-size: 11px;
}

.distribution-values strong {
  color: var(--vf-dark);
  font-size: 15px;
  font-variant-numeric: tabular-nums;
}

.per-class-wrap {
  margin-top: 24px;
}

.per-class-scroll {
  overflow-x: auto;
}

.per-class-table {
  min-width: 560px;
  overflow: hidden;
  border: 1px solid var(--vf-border-light);
  border-radius: 10px;
}

.per-class-row {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) repeat(5, minmax(0, 1fr));
  gap: 0;
}

.per-class-row + .per-class-row {
  border-top: 1px solid var(--vf-border-light);
}

.per-class-row > * {
  display: flex;
  align-items: center;
  padding: 9px 11px;
  color: var(--vf-dark);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.per-class-row > * + * {
  border-left: 1px solid var(--vf-border-light);
}

.per-class-row strong {
  overflow-wrap: anywhere;
  font-size: 12px;
}

.per-class-header > * {
  color: var(--vf-muted);
  background: #fafafa;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

@media (max-width: 1000px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .metric-item + .metric-item {
    border-left: 0;
    border-top: 1px solid var(--vf-border-light);
  }

  .evaluation-bottom {
    grid-template-columns: 1fr;
  }
}
</style>
