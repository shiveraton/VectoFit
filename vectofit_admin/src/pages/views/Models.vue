<script setup lang="ts">
import { computed } from "vue";
import { useModels } from "../../hooks/useModels";
import ModelEvaluationState from "../../components/models/ModelEvaluationState.vue";
import ModelFeatureState from "../../components/models/ModelFeatureState.vue";
import ModelRegistryTable from "../../components/models/ModelRegistryTable.vue";

const {
  models,
  modelState,
  selectedModelId,
  summaryCards,
  isLoading,
  isStateLoading,
  error,
  isActivatingModel,
  activationMessage,
  selectModel,
  activateModel,
} = useModels();

const statusLabel = computed(() => {
  const model = modelState.value;

  if (!model) return "NO MODEL";

  return model.is_active ? "ACTIVE" : "REGISTERED";
});

const canActivateModel = computed(() => {
  const model = modelState.value;

  if (!model) return false;

  return (
    !model.is_active &&
    Boolean(model.view_angle) &&
    model.training.status === "COMPLETED" &&
    model.artifact_available
  );
});

const predictionTargetLabel = computed(() => {
  switch (modelState.value?.prediction_target) {
    case "binary_form":
      return "Good / Bad Form";

    case "error_type":
      return "Error Type";

    default:
      return "Unspecified";
  }
});

const cameraAngleLabel = computed(() => {
  const angle = modelState.value?.view_angle;

  if (!angle) return "Legacy / unspecified";

  return angle.charAt(0).toUpperCase() + angle.slice(1);
});

const selectedDatasetText = computed(() => {
  const datasetNames = modelState.value?.training.dataset_names ?? [];

  return datasetNames.length ? datasetNames.join(", ") : "No dataset recorded";
});

const evaluationAvailable = computed(() => {
  const model = modelState.value;

  if (
    !model ||
    model.training.status !== "COMPLETED" ||
    model.training.test_count <= 0
  ) {
    return false;
  }

  const evaluation = model.evaluation;

  return [
    evaluation.accuracy,
    evaluation.balanced_accuracy,
    evaluation.precision,
    evaluation.recall,
    evaluation.f1,
  ].some((metric) => metric != null);
});

const formatDate = (value: string | null | undefined): string => {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};
</script>

<template>
  <div class="models-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          VECTOFIT MODEL STATE
        </div>

        <h1>Models</h1>

        <p>
          Inspect model provenance and held-out performance, then activate a
          validated version for its camera angle and prediction target.
        </p>
      </div>
    </header>

    <div v-if="error" class="error-banner" role="alert">
      {{ error }}
    </div>

    <div v-if="activationMessage" class="activation-banner" role="status">
      {{ activationMessage }}
    </div>

    <section
      v-if="isLoading && models.length === 0"
      class="content-card loading-card"
      aria-live="polite"
    >
      Loading model registry…
    </section>

    <section
      v-else-if="!isLoading && models.length === 0"
      class="content-card empty-state-card"
    >
      <div class="empty-state-icon">M</div>

      <h2>No registered models yet</h2>

      <p>
        Complete a successful training run that saves a model artifact and
        creates its registry record. Registered model versions will appear here.
      </p>
    </section>

    <template v-else>
      <div v-if="isStateLoading" class="state-loading" aria-live="polite">
        Loading selected model state…
      </div>

      <template v-else-if="modelState">
        <section class="hero-card">
          <div class="hero-information">
            <div class="model-kicker">
              {{ modelState.algorithm }}
            </div>

            <div class="model-title-row">
              <h2>{{ modelState.name }}</h2>

              <span class="version-badge"> v{{ modelState.version }} </span>
            </div>

            <p class="model-caption">
              Trained from job #{{ modelState.training.job_id }} · Created
              {{ formatDate(modelState.created_at) }}
            </p>
          </div>

          <div class="hero-actions">
            <span class="state-badge" :class="{ active: modelState.is_active }">
              {{ statusLabel }}
            </span>

            <button
              v-if="canActivateModel"
              class="activate-button"
              type="button"
              :disabled="isActivatingModel"
              @click="activateModel(modelState.id)"
            >
              {{ isActivatingModel ? "Activating…" : "Activate for inference" }}
            </button>
          </div>
        </section>

        <section class="summary-grid" aria-label="Model summary">
          <div
            v-for="card in summaryCards"
            :key="card.label"
            class="summary-card"
          >
            <span>{{ card.label }}</span>
            <strong>{{ card.value }}</strong>
            <small>{{ card.description }}</small>
          </div>
        </section>

        <section class="content-card">
          <div class="section-header">
            <div class="section-title-row">
              <div class="section-marker"></div>

              <div>
                <h2>Model &amp; Training Provenance</h2>
                <p>Where this version came from and how it was trained.</p>
              </div>
            </div>
          </div>

          <div class="provenance-grid">
            <div>
              <span>Algorithm</span>
              <strong>{{ modelState.algorithm }}</strong>
            </div>

            <div>
              <span>Camera angle</span>
              <strong>{{ cameraAngleLabel }}</strong>
            </div>

            <div>
              <span>Prediction target</span>
              <strong>{{ predictionTargetLabel }}</strong>
            </div>

            <div>
              <span>Feature schema</span>
              <strong>{{ modelState.feature_schema_version || "—" }}</strong>
            </div>

            <div>
              <span>Training status</span>
              <strong>{{ modelState.training.status }}</strong>
            </div>

            <div>
              <span>Dataset</span>
              <strong>{{ selectedDatasetText }}</strong>
            </div>

            <div>
              <span>Total samples</span>
              <strong>{{ modelState.training.sample_count }}</strong>
            </div>

            <div>
              <span>Train / test samples</span>
              <strong>
                {{ modelState.training.train_count }}
                /
                {{ modelState.training.test_count }}
              </strong>
            </div>

            <div>
              <span>Split strategy</span>
              <strong>{{ modelState.training.split_strategy || "—" }}</strong>
            </div>

            <div>
              <span>Random seed</span>
              <strong>{{ modelState.training.random_seed ?? "—" }}</strong>
            </div>

            <div>
              <span>Training started</span>
              <strong>
                {{ formatDate(modelState.training.started_at) }}
              </strong>
            </div>

            <div>
              <span>Training completed</span>
              <strong>
                {{ formatDate(modelState.training.completed_at) }}
              </strong>
            </div>
          </div>
        </section>

        <section class="content-card">
          <div class="section-header">
            <div class="section-title-row">
              <div class="section-marker"></div>

              <div>
                <h2>Feature Set</h2>
                <p>
                  Features recorded for this training run and used by the
                  classifier.
                </p>
              </div>
            </div>

            <span class="section-badge">
              {{ modelState.features.selected.length }} FEATURES
            </span>
          </div>

          <ModelFeatureState :features="modelState.features" />
        </section>

        <section class="content-card evaluation-card">
          <div class="section-header">
            <div class="section-title-row">
              <div class="section-marker"></div>

              <div>
                <h2>Evaluation Results</h2>
                <p>
                  Performance measured using held-out test samples from this
                  model's training run.
                </p>
              </div>
            </div>

            <span class="section-badge" :class="{ ready: evaluationAvailable }">
              {{ evaluationAvailable ? "EVALUATED" : "NO RESULTS" }}
            </span>
          </div>

          <template v-if="evaluationAvailable">
            <div class="evaluation-context">
              <div>
                <span>Training job</span>
                <strong>#{{ modelState.training.job_id }}</strong>
              </div>

              <div>
                <span>Test samples</span>
                <strong>{{ modelState.training.test_count }}</strong>
              </div>

              <div>
                <span>Prediction target</span>
                <strong>{{ predictionTargetLabel }}</strong>
              </div>

              <div>
                <span>Camera angle</span>
                <strong>{{ cameraAngleLabel }}</strong>
              </div>
            </div>

            <ModelEvaluationState :evaluation="modelState.evaluation" />

            <p class="evaluation-note">
              These are offline evaluation results from the held-out test set.
              They are not live predictions from the smartphone camera.
              Selecting another registered version displays that version's saved
              evaluation.
            </p>
          </template>

          <div v-else class="empty-detail">
            <strong>No evaluation results available</strong>

            <p>
              This model does not have completed evaluation metrics and a
              non-empty test set recorded in its saved state.
            </p>
          </div>
        </section>

        <section
          v-if="modelState.feature_warnings.length > 0"
          class="content-card warning-card"
        >
          <div class="section-header">
            <div class="section-title-row">
              <div class="section-marker"></div>

              <div>
                <h2>Validation &amp; Feature Warnings</h2>
                <p>Scientific caveats recorded while producing this model.</p>
              </div>
            </div>

            <span class="section-badge warning-badge">
              {{ modelState.feature_warnings.length }} WARNINGS
            </span>
          </div>

          <div class="warning-list">
            <div
              v-for="(warning, index) in modelState.feature_warnings"
              :key="`${index}-${warning}`"
              class="warning-item"
            >
              {{ warning }}
            </div>
          </div>
        </section>
      </template>

      <section
        v-else-if="selectedModelId !== null"
        class="content-card empty-detail"
        role="status"
      >
        <strong>Unable to display the selected model</strong>

        <p>
          The registry is available, but the details for this model could not be
          loaded. Check the error message above and try selecting the version
          again.
        </p>

        <button
          class="secondary-button"
          type="button"
          @click="selectModel(selectedModelId)"
        >
          Retry loading model
        </button>
      </section>

      <section class="content-card registry-card">
        <div class="section-header">
          <div class="section-title-row">
            <div class="section-marker"></div>

            <div>
              <h2>Model Registry</h2>
              <p>
                Select a registered version to inspect its provenance, features,
                and evaluation results.
              </p>
            </div>
          </div>

          <span class="section-badge">
            {{ models.length }}
            {{ models.length === 1 ? "VERSION" : "VERSIONS" }}
          </span>
        </div>

        <ModelRegistryTable
          :models="models"
          :selected-model-id="selectedModelId"
          @select="selectModel"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
.models-page {
  min-height: 100%;
  padding: 32px;
  background: var(--vf-background);
  font-family: "Segoe UI", Arial, sans-serif;
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
  text-transform: uppercase;
}

.eyebrow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--vf-orange);
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.12);
}

.page-header h1 {
  margin: 0 0 5px;
  color: var(--vf-dark);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.page-header p {
  max-width: 720px;
  margin: 0;
  color: var(--vf-muted);
  font-size: 13px;
  line-height: 1.6;
}

.error-banner,
.activation-banner {
  margin-bottom: 18px;
  padding: 11px 14px;
  border-radius: 8px;
  font-size: 11px;
  line-height: 1.6;
}

.error-banner {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.activation-banner {
  border: 1px solid #a7f3d0;
  background: #ecfdf3;
  color: #047857;
}

.loading-card {
  padding: 26px;
  color: var(--vf-muted);
  font-size: 12px;
}

.state-loading {
  margin-bottom: 14px;
  padding: 10px 12px;
  border: 1px solid var(--vf-border-light);
  border-radius: 8px;
  background: #fff;
  color: var(--vf-muted);
  font-size: 11px;
}

.empty-state-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 28px;
}

.empty-state-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  margin-bottom: 14px;
  border-radius: 10px;
  background: #fff7ed;
  color: var(--vf-orange);
  font-size: 15px;
  font-weight: 800;
}

.empty-state-card h2 {
  margin: 0 0 8px;
  color: var(--vf-dark);
  font-size: 16px;
}

.empty-state-card p,
.empty-detail p {
  max-width: 650px;
  margin: 0;
  color: var(--vf-muted);
  font-size: 11px;
  line-height: 1.7;
}

.empty-detail {
  padding: 22px;
  color: var(--vf-muted);
  font-size: 11px;
}

.empty-detail > strong {
  display: block;
  margin-bottom: 7px;
  color: var(--vf-dark);
  font-size: 12px;
}

.secondary-button {
  margin-top: 14px;
  padding: 8px 12px;
  border: 1px solid var(--vf-border-light);
  border-radius: 8px;
  background: #fff;
  color: var(--vf-dark);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.secondary-button:hover {
  background: var(--vf-background);
}

.hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 24px;
  margin-bottom: 14px;
  border: 1px solid var(--vf-border-light);
  border-radius: 12px;
  background: linear-gradient(135deg, #fff, #fffaf6);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.hero-information {
  min-width: 0;
}

.model-kicker {
  color: var(--vf-orange);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.model-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 5px;
}

.model-title-row h2 {
  margin: 0;
  color: var(--vf-dark);
  font-size: 21px;
  overflow-wrap: anywhere;
}

.version-badge,
.section-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(249, 115, 22, 0.08);
  color: var(--vf-orange);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.model-caption {
  margin: 7px 0 0;
  color: var(--vf-muted);
  font-size: 11px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.state-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #f4f4f5;
  color: #71717a;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.state-badge.active {
  background: #fff7ed;
  color: var(--vf-orange);
}

.activate-button {
  padding: 8px 12px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 0.15s ease,
    opacity 0.15s ease;
}

.activate-button:hover:not(:disabled) {
  background: #ffedd5;
}

.activate-button:disabled {
  opacity: 0.55;
  cursor: wait;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.summary-card {
  min-width: 0;
  padding: 16px;
  border: 1px solid var(--vf-border-light);
  border-radius: 10px;
  background: #fff;
}

.summary-card span {
  display: block;
  color: var(--vf-muted);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.summary-card strong {
  display: block;
  margin-top: 8px;
  color: var(--vf-dark);
  font-size: 21px;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}

.summary-card small {
  display: block;
  margin-top: 5px;
  color: var(--vf-muted);
  font-size: 10px;
  line-height: 1.5;
}

.content-card {
  margin-bottom: 18px;
  overflow: hidden;
  border: 1px solid var(--vf-border-light);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 17px 20px;
  border-bottom: 1px solid var(--vf-border-light);
}

.section-title-row {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  min-width: 0;
}

.section-marker {
  width: 3px;
  min-width: 3px;
  height: 17px;
  margin-top: 1px;
  border-radius: 4px;
  background: var(--vf-gradient);
}

.section-header h2 {
  margin: 0;
  color: var(--vf-dark);
  font-size: 14px;
}

.section-header p {
  margin: 4px 0 0;
  color: var(--vf-muted);
  font-size: 10px;
  line-height: 1.6;
}

.section-badge.ready {
  background: #f0fdf4;
  color: #15803d;
}

.warning-badge {
  background: #fff7ed;
  color: #9a3412;
}

.provenance-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.provenance-grid > div {
  min-width: 0;
  padding: 16px 18px;
  border-right: 1px solid var(--vf-border-light);
  border-bottom: 1px solid var(--vf-border-light);
}

.provenance-grid > div:nth-child(4n) {
  border-right: 0;
}

.provenance-grid > div span {
  display: block;
  margin-bottom: 5px;
  color: var(--vf-muted);
  font-size: 10px;
}

.provenance-grid > div strong {
  display: block;
  color: var(--vf-dark);
  font-size: 11px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.evaluation-context {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 20px 20px;
}

.evaluation-context > div {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  padding: 13px;
  border: 1px solid var(--vf-border-light);
  border-radius: 8px;
  background: #fff;
}

.evaluation-context span {
  color: var(--vf-muted);
  font-size: 10px;
}

.evaluation-context strong {
  color: var(--vf-dark);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.evaluation-note {
  margin: 18px 20px 20px;
  padding-top: 14px;
  border-top: 1px solid var(--vf-border-light);
  color: var(--vf-muted);
  font-size: 11px;
  line-height: 1.7;
}

.warning-card {
  border-color: #fed7aa;
}

.warning-list {
  display: grid;
  gap: 8px;
  padding: 18px 20px;
}

.warning-item {
  padding: 10px 12px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 11px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .provenance-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .provenance-grid > div:nth-child(4n) {
    border-right: 1px solid var(--vf-border-light);
  }

  .provenance-grid > div:nth-child(2n) {
    border-right: 0;
  }

  .evaluation-context {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .models-page {
    padding: 20px;
  }

  .hero-card {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-actions {
    justify-content: flex-start;
    width: 100%;
  }

  .summary-grid,
  .provenance-grid,
  .evaluation-context {
    grid-template-columns: 1fr;
  }

  .provenance-grid > div,
  .provenance-grid > div:nth-child(4n),
  .provenance-grid > div:nth-child(2n) {
    border-right: 0;
  }

  .section-header {
    align-items: flex-start;
  }
}
</style>
