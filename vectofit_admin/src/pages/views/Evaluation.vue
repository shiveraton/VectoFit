<script setup lang="ts">
import { computed } from "vue";
import { useEvaluation } from "../../hooks/useEvaluation";

const {
  models,
  selectedModelId,
  modelState,
  evaluation,
  training,
  summaryCards,
  evaluationAvailable,
  isLoading,
  isStateLoading,
  error,
  selectModel,
  fetchModels,
  formatPercent,
  formatDate,
  formatAngle,
  formatTarget,
} = useEvaluation();

const confusionMatrix = computed(
  () => evaluation.value?.confusion_matrix ?? [],
);

const classDistribution = computed(() =>
  Object.entries(evaluation.value?.test_class_distribution ?? {}),
);

const selectedDatasetNames = computed(
  () => training.value?.dataset_names ?? [],
);

const selectedFeatures = computed(
  () => modelState.value?.features.selected ?? [],
);

const featureWarnings = computed(
  () => modelState.value?.feature_warnings ?? [],
);

const handleModelChange = async (event: Event) => {
  const value = (event.target as HTMLSelectElement).value;
  const id = Number(value);

  if (Number.isInteger(id) && id > 0) {
    await selectModel(id);
  }
};
</script>

<template>
  <main class="evaluation-page">
    <header class="page-header">
      <div>
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          VECTOFIT MODEL EVALUATION
        </div>

        <h1>Evaluation</h1>

        <p>
          Review the held-out test performance of models registered by the
          training pipeline.
        </p>
      </div>

      <button
        class="secondary-button"
        type="button"
        :disabled="isLoading || isStateLoading"
        @click="fetchModels"
      >
        {{ isLoading ? "Refreshing…" : "Refresh results" }}
      </button>
    </header>

    <div v-if="error" class="message error-message" role="alert">
      <strong>Could not load evaluation data</strong>
      <p>{{ error }}</p>
    </div>

    <section v-if="isLoading && !models.length" class="panel loading-panel">
      Loading registered models…
    </section>

    <section v-else-if="!models.length && !isLoading" class="panel empty-panel">
      <h2>No registered models yet</h2>
      <p>
        Complete a training job first. Successfully registered models will
        appear here with their saved evaluation results.
      </p>
    </section>

    <template v-else>
      <section class="panel model-selector-panel">
        <div class="section-heading">
          <div>
            <h2>Registered model</h2>
            <p>Select a model to inspect its saved evaluation results.</p>
          </div>

          <span
            v-if="modelState"
            class="status-badge"
            :class="{ active: modelState.is_active }"
          >
            {{ modelState.is_active ? "ACTIVE FOR INFERENCE" : "REGISTERED" }}
          </span>
        </div>

        <label class="field-label" for="evaluation-model"> Model </label>

        <select
          id="evaluation-model"
          class="model-select"
          :value="selectedModelId ?? ''"
          :disabled="isStateLoading"
          @change="handleModelChange"
        >
          <option v-for="model in models" :key="model.id" :value="model.id">
            {{ model.name }} · v{{ model.version }} ·
            {{ formatTarget(model.prediction_target) }} ·
            {{ formatAngle(model.view_angle) }}
          </option>
        </select>

        <p v-if="isStateLoading" class="muted loading-inline">
          Loading the selected model's evaluation state…
        </p>
      </section>

      <template v-if="modelState && !isStateLoading">
        <section class="model-overview">
          <div class="model-title">
            <div>
              <div class="model-kicker">
                {{ modelState.algorithm }}
              </div>
              <h2>{{ modelState.name }}</h2>
              <p>
                Version {{ modelState.version }} · Training job #{{
                  modelState.training.job_id
                }}
              </p>
            </div>

            <span
              class="status-badge"
              :class="{ active: modelState.is_active }"
            >
              {{ modelState.is_active ? "ACTIVE" : "REGISTERED" }}
            </span>
          </div>

          <div class="metadata-grid">
            <div class="metadata-item">
              <span>Camera angle</span>
              <strong>{{ formatAngle(modelState.view_angle) }}</strong>
            </div>

            <div class="metadata-item">
              <span>Prediction target</span>
              <strong>{{ formatTarget(modelState.prediction_target) }}</strong>
            </div>

            <div class="metadata-item">
              <span>Feature schema</span>
              <strong>{{ modelState.feature_schema_version || "—" }}</strong>
            </div>

            <div class="metadata-item">
              <span>Artifact</span>
              <strong>
                {{ modelState.artifact_available ? "Available" : "Missing" }}
              </strong>
            </div>

            <div class="metadata-item">
              <span>Training status</span>
              <strong>{{ training?.status ?? "—" }}</strong>
            </div>

            <div class="metadata-item">
              <span>Created</span>
              <strong>{{ formatDate(modelState.created_at) }}</strong>
            </div>
          </div>
        </section>

        <section class="section-block">
          <div class="section-heading">
            <div>
              <h2>Held-out test performance</h2>
              <p>
                These are saved training-evaluation metrics, not scores from a
                live phone assessment.
              </p>
            </div>

            <span class="status-badge" :class="{ active: evaluationAvailable }">
              {{ evaluationAvailable ? "RESULTS AVAILABLE" : "NO RESULTS" }}
            </span>
          </div>

          <div v-if="evaluationAvailable" class="metric-grid">
            <article
              v-for="card in summaryCards"
              :key="card.label"
              class="metric-card"
            >
              <span class="metric-label">{{ card.label }}</span>
              <strong class="metric-value">{{ card.value }}</strong>
              <p>{{ card.description }}</p>
            </article>
          </div>

          <div v-else class="panel empty-panel">
            <h3>Evaluation metrics unavailable</h3>
            <p>
              This model does not have completed held-out evaluation results.
              Check the training job status and its saved metrics.
            </p>
          </div>

          <div v-if="evaluation" class="secondary-metrics">
            <div class="secondary-metric">
              <span>Recall</span>
              <strong>{{ formatPercent(evaluation.recall) }}</strong>
            </div>
            <div class="secondary-metric">
              <span>Test samples</span>
              <strong>{{ training?.test_count ?? "—" }}</strong>
            </div>
            <div class="secondary-metric">
              <span>Training samples</span>
              <strong>{{ training?.train_count ?? "—" }}</strong>
            </div>
            <div class="secondary-metric">
              <span>Total samples</span>
              <strong>{{ training?.sample_count ?? "—" }}</strong>
            </div>
          </div>
        </section>

        <section class="section-block">
          <div class="section-heading">
            <div>
              <h2>Training data and split</h2>
              <p>
                Dataset provenance and how the evaluation data was separated.
              </p>
            </div>
          </div>

          <div class="panel details-panel">
            <div class="detail-row">
              <span>Datasets</span>
              <div v-if="selectedDatasetNames.length" class="chip-list">
                <span
                  v-for="name in selectedDatasetNames"
                  :key="name"
                  class="data-chip"
                >
                  {{ name }}
                </span>
              </div>
              <strong v-else>No dataset names recorded</strong>
            </div>

            <div class="detail-row">
              <span>Split strategy</span>
              <strong>{{ training?.split_strategy || "—" }}</strong>
            </div>

            <div class="detail-row">
              <span>Test size</span>
              <strong>
                {{
                  training?.test_size != null
                    ? formatPercent(training.test_size)
                    : "—"
                }}
              </strong>
            </div>

            <div class="detail-row">
              <span>Random seed</span>
              <strong>{{ training?.random_seed ?? "—" }}</strong>
            </div>

            <div class="detail-row">
              <span>Completed at</span>
              <strong>{{ formatDate(training?.completed_at) }}</strong>
            </div>

            <div class="detail-row">
              <span>Selected features</span>
              <div v-if="selectedFeatures.length" class="chip-list">
                <span
                  v-for="feature in selectedFeatures"
                  :key="feature"
                  class="data-chip"
                >
                  {{ feature }}
                </span>
              </div>
              <strong v-else>No selected features recorded</strong>
            </div>
          </div>
        </section>

        <section class="section-block">
          <div class="section-heading">
            <div>
              <h2>Confusion matrix</h2>
              <p>
                Rows and columns follow the classifier's class order. Values
                come from the saved held-out test evaluation.
              </p>
            </div>
          </div>

          <div v-if="confusionMatrix.length" class="panel matrix-panel">
            <div class="matrix-scroll">
              <table class="matrix-table">
                <caption>
                  Actual classes by predicted classes
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Actual \ Predicted</th>
                    <th
                      v-for="(_, index) in confusionMatrix[0]"
                      :key="`predicted-${index}`"
                      scope="col"
                    >
                      Class {{ index }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(row, rowIndex) in confusionMatrix"
                    :key="`actual-${rowIndex}`"
                  >
                    <th scope="row">Class {{ rowIndex }}</th>
                    <td v-for="(value, colIndex) in row" :key="colIndex">
                      {{ value }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <p class="muted matrix-note">
              Class names are shown as indices because the state response does
              not expose an explicit class-label ordering in this table.
            </p>
          </div>

          <div v-else class="panel empty-panel">
            No confusion matrix is available for this model.
          </div>
        </section>

        <section v-if="classDistribution.length" class="section-block">
          <div class="section-heading">
            <div>
              <h2>Test-set class distribution</h2>
              <p>
                Number of samples in each class used for held-out evaluation.
              </p>
            </div>
          </div>

          <div class="panel details-panel">
            <div
              v-for="[label, count] in classDistribution"
              :key="label"
              class="detail-row"
            >
              <span>{{ label }}</span>
              <strong>{{ count }}</strong>
            </div>
          </div>
        </section>

        <section v-if="featureWarnings.length" class="section-block">
          <div class="section-heading">
            <div>
              <h2>Feature warnings</h2>
              <p>Warnings returned by the registered model's state endpoint.</p>
            </div>
          </div>

          <div class="message warning-message">
            <ul>
              <li v-for="warning in featureWarnings" :key="warning">
                {{ warning }}
              </li>
            </ul>
          </div>
        </section>
      </template>
    </template>
  </main>
</template>

<style scoped>
.evaluation-page {
  min-height: 100%;
  padding: 32px;
  background: var(--vf-background);
  color: var(--vf-text);
  font-family: "Segoe UI", Arial, sans-serif;
}

.page-header,
.section-heading,
.model-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.page-header {
  margin-bottom: 24px;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
  color: var(--vf-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.eyebrow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--vf-orange);
}

.page-header h1,
.model-title h2 {
  margin: 0 0 7px;
  color: var(--vf-dark);
  font-size: 27px;
}

.page-header p,
.model-title p,
.section-heading p {
  margin: 0;
  color: var(--vf-muted);
  font-size: 12px;
  line-height: 1.6;
}

.secondary-button {
  padding: 10px 14px;
  border: 1px solid var(--vf-border);
  border-radius: 8px;
  background: white;
  color: var(--vf-text);
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}

.secondary-button:disabled {
  cursor: wait;
  opacity: 0.6;
}

.panel,
.model-overview,
.metric-card {
  border: 1px solid var(--vf-border);
  border-radius: 10px;
  background: var(--vf-surface);
  box-shadow: 0 1px 2px rgba(24, 24, 27, 0.025);
}

.panel {
  padding: 20px;
}

.model-selector-panel {
  margin-bottom: 20px;
}

.section-heading {
  margin-bottom: 18px;
}

.section-heading h2,
.empty-panel h2,
.empty-panel h3 {
  margin: 0 0 5px;
  color: var(--vf-dark);
  font-size: 15px;
}

.field-label {
  display: block;
  margin-bottom: 7px;
  color: var(--vf-muted);
  font-size: 11px;
  font-weight: 700;
}

.model-select {
  width: 100%;
  max-width: 720px;
  padding: 11px 12px;
  border: 1px solid var(--vf-border);
  border-radius: 8px;
  background: #fff;
  color: var(--vf-text);
  font: inherit;
  font-size: 13px;
}

.status-badge {
  display: inline-flex;
  flex-shrink: 0;
  padding: 6px 9px;
  border-radius: 6px;
  background: #f4f4f5;
  color: #52525b;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.04em;
}

.status-badge.active {
  background: #ecfdf3;
  color: #047857;
}

.model-overview {
  margin-bottom: 26px;
  padding: 22px;
}

.model-kicker {
  margin-bottom: 7px;
  color: var(--vf-orange-dark);
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--vf-border-light);
}

.metadata-item,
.secondary-metric {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.metadata-item span,
.secondary-metric span {
  color: var(--vf-muted);
  font-size: 11px;
}

.metadata-item strong,
.secondary-metric strong {
  overflow-wrap: anywhere;
  color: var(--vf-dark);
  font-size: 12px;
}

.section-block {
  margin-bottom: 28px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 18px;
}

.metric-label {
  display: block;
  color: var(--vf-muted);
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.06em;
}

.metric-value {
  display: block;
  margin-top: 12px;
  color: var(--vf-dark);
  font-size: 27px;
  letter-spacing: -0.03em;
}

.metric-card p {
  margin: 8px 0 0;
  color: var(--vf-muted);
  font-size: 11px;
  line-height: 1.5;
}

.secondary-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
  padding: 18px;
  border: 1px solid var(--vf-border);
  border-radius: 10px;
  background: #fff;
}

.details-panel {
  padding: 4px 20px;
}

.detail-row {
  display: grid;
  grid-template-columns: minmax(130px, 0.7fr) minmax(0, 2fr);
  align-items: center;
  gap: 18px;
  padding: 14px 0;
  border-bottom: 1px solid var(--vf-border-light);
  font-size: 12px;
}

.detail-row:last-child {
  border-bottom: 0;
}

.detail-row > span {
  color: var(--vf-muted);
}

.detail-row > strong {
  overflow-wrap: anywhere;
  color: var(--vf-dark);
  font-weight: 600;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.data-chip {
  max-width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--vf-border);
  border-radius: 6px;
  background: #fafafa;
  color: var(--vf-text);
  font-size: 11px;
  overflow-wrap: anywhere;
}

.matrix-panel {
  padding: 18px;
}

.matrix-scroll {
  overflow-x: auto;
}

.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  text-align: center;
}

.matrix-table caption {
  margin-bottom: 12px;
  color: var(--vf-muted);
  text-align: left;
}

.matrix-table th,
.matrix-table td {
  min-width: 84px;
  padding: 12px;
  border: 1px solid var(--vf-border);
}

.matrix-table th {
  background: #fafafa;
  font-weight: 700;
}

.matrix-note {
  margin-bottom: 0;
}

.message {
  margin-bottom: 20px;
  padding: 14px 16px;
  border: 1px solid var(--vf-border);
  border-radius: 8px;
  background: white;
  font-size: 12px;
}

.message p {
  margin: 6px 0 0;
  line-height: 1.6;
}

.error-message {
  border-color: #fecaca;
  background: #fef2f2;
  color: #991b1b;
}

.warning-message {
  border-color: #fde68a;
  background: #fffbeb;
  color: #92400e;
}

.warning-message ul {
  margin: 0;
  padding-left: 20px;
}

.warning-message li + li {
  margin-top: 7px;
}

.empty-panel {
  color: var(--vf-muted);
  font-size: 12px;
  line-height: 1.6;
}

.empty-panel p {
  margin: 7px 0 0;
}

.loading-panel {
  color: var(--vf-muted);
  font-size: 12px;
}

.loading-inline,
.muted {
  color: var(--vf-muted);
  font-size: 11px;
  line-height: 1.6;
}

@media (max-width: 1000px) {
  .metadata-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-grid,
  .secondary-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 650px) {
  .evaluation-page {
    padding: 18px;
  }

  .page-header,
  .section-heading,
  .model-title {
    flex-direction: column;
    align-items: flex-start;
  }

  .metadata-grid,
  .metric-grid,
  .secondary-metrics {
    grid-template-columns: 1fr;
  }

  .detail-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }
}
</style>
