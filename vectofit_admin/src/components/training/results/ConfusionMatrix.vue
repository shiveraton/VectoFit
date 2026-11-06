<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  matrix: unknown;
  labels?: string[] | null;
}>();

const entries = computed<number[][] | null>(() => {
  const matrix = props.matrix;

  if (!Array.isArray(matrix) || matrix.length === 0) {
    return null;
  }

  const size = matrix.length;
  const parsed: number[][] = [];

  for (const row of matrix) {
    if (!Array.isArray(row) || row.length !== size) {
      return null;
    }

    const values = row.map((value) => Number(value));
    if (values.some((value) => !Number.isFinite(value))) {
      return null;
    }

    parsed.push(values);
  }

  return parsed;
});

const matrixSize = computed(() => entries.value?.length ?? 0);

const classLabels = computed(() => {
  const size = matrixSize.value;
  const provided = (props.labels ?? []).filter(
    (label): label is string => typeof label === "string" && label.trim() !== "",
  );

  if (provided.length === size) {
    return provided;
  }

  if (size === 2) {
    return ["Bad", "Good"];
  }

  return Array.from({ length: size }, (_, index) => `Class ${index}`);
});

const humanize = (label: string) =>
  label
    .replace(/_/g, " ")
    .trim()
    .split(/\s+/)
    .map((word) =>
      word.length
        ? word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        : word,
    )
    .join(" ");

const rowTotal = (row: number[]) =>
  row.reduce((total, value) => total + value, 0);

const cellPercent = (rowIndex: number, columnIndex: number) => {
  const row = entries.value?.[rowIndex];
  if (!row) return 0;

  const total = rowTotal(row);
  return total > 0 ? Math.round((row[columnIndex] / total) * 100) : 0;
};

const summary = computed(() => {
  return "Rows are the human-reviewed FPPA labels (bad or good); columns are the model predictions. Inspect which knee-alignment class is confused before activating the model.";
});
</script>

<template>
  <section class="result-panel">
    <header class="result-panel-header">
      <div>
        <h3>Classification Results</h3>
        <p>
          How predictions compared with the known test-set labels. Rows are
          actual labels; columns are predicted labels.
        </p>
      </div>
    </header>

    <div v-if="entries" class="matrix-legend">
      <span v-for="(label, index) in classLabels" :key="`legend-${index}`">
        <strong>{{ index }}</strong> = {{ humanize(label) }}
      </span>
    </div>

    <div v-if="entries" class="matrix-scroll">
      <div class="matrix-layout" :style="{ '--matrix-size': matrixSize }">
        <div class="matrix-axis axis-corner">Actual ↓ / Predicted →</div>
        <div
          v-for="(label, index) in classLabels"
          :key="`column-${index}`"
          class="matrix-axis column-label"
          :title="humanize(label)"
        >
          {{ humanize(label) }}
        </div>

        <template
          v-for="(row, rowIndex) in entries"
          :key="`row-${rowIndex}`"
        >
          <div class="matrix-axis row-label">
            {{ humanize(classLabels[rowIndex] ?? `Class ${rowIndex}`) }}
          </div>
          <div
            v-for="(count, columnIndex) in row"
            :key="`cell-${rowIndex}-${columnIndex}`"
            :class="[
              'matrix-cell',
              rowIndex === columnIndex ? 'correct' : 'misclassified',
            ]"
          >
            <strong>{{ count }}</strong>
            <span>
              {{ cellPercent(rowIndex, columnIndex) }}% of actual
              {{ humanize(classLabels[rowIndex] ?? `Class ${rowIndex}`).toLowerCase() }}
            </span>
          </div>
        </template>
      </div>
    </div>

    <div v-else class="panel-empty">
      No confusion matrix is available for this run.
    </div>

    <div v-if="entries" class="matrix-summary">
      <strong>What to watch:</strong> {{ summary }}
    </div>
  </section>
</template>

<style scoped>
.result-panel {
  min-width: 0;
  padding: 18px;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 10px;
}

.result-panel-header h3 {
  margin: 0;
  color: var(--vf-text);
  font-size: 12px;
}

.result-panel-header p {
  margin: 4px 0 0;
  color: var(--vf-light-muted);
  font-size: 11px;
  line-height: 1.5;
}

.matrix-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 13px;
  color: var(--vf-light-muted);
  font-size: 12px;
}

.matrix-legend strong {
  color: var(--vf-text);
}

.matrix-scroll {
  margin-top: 14px;
  overflow-x: auto;
}

.matrix-layout {
  display: grid;
  grid-template-columns: 92px repeat(var(--matrix-size, 2), minmax(0, 1fr));
  gap: 6px;
}

.matrix-axis {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 4px;
  color: var(--vf-light-muted);
  background: #fafafa;
  border: 1px solid var(--vf-border-light);
  border-radius: 6px;
  text-align: center;
  overflow-wrap: anywhere;
  font-size: 12px;
  font-weight: 700;
}

.axis-corner {
  line-height: 1.25;
}

.column-label,
.row-label {
  color: var(--vf-muted);
}

.matrix-cell {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 78px;
  padding: 8px;
  border: 1px solid var(--vf-border-light);
  border-radius: 7px;
  text-align: center;
}

.matrix-cell strong {
  color: var(--vf-dark);
  font-size: 20px;
}

.matrix-cell span {
  margin-top: 4px;
  color: var(--vf-muted);
  font-size: 12px;
  line-height: 1.35;
}

.matrix-cell.correct {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.matrix-cell.misclassified {
  background: #fffbeb;
  border-color: #fde68a;
}

.panel-empty {
  margin-top: 14px;
  padding: 18px;
  color: var(--vf-light-muted);
  background: #fafafa;
  border: 1px dashed var(--vf-border);
  border-radius: 8px;
  text-align: center;
  font-size: 11px;
}

.matrix-summary {
  margin-top: 12px;
  padding: 10px;
  color: var(--vf-muted);
  background: #fffaf6;
  border: 1px solid #fed7aa;
  border-radius: 7px;
  font-size: 11px;
  line-height: 1.5;
}

.matrix-summary strong {
  color: var(--vf-text);
}

@media (max-width: 500px) {
  .matrix-layout {
    grid-template-columns: 72px repeat(var(--matrix-size, 2), minmax(0, 1fr));
  }

  .matrix-cell {
    min-height: 64px;
    padding: 6px;
  }

  .matrix-cell strong {
    font-size: 16px;
  }

  .matrix-cell span {
    font-size: 7px;
  }
}
</style>
