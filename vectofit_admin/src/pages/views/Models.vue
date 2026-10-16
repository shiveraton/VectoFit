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
  selectModel,
} = useModels();

const statusLabel = computed(() => {
  if (!modelState.value) return "NO MODEL";
  return modelState.value.is_active ? "ACTIVE" : "REGISTERED";
});

const formatDate = (value: string | null | undefined) => {
  if (!value) return "—";

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
};

const selectedDatasetText = computed(() => {
  const names = modelState.value?.training.dataset_names ?? [];

  return names.length ? names.join(", ") : "No dataset recorded";
});

const evaluationAvailable = computed(
  () =>
    modelState.value?.training.status === "COMPLETED" &&
    modelState.value?.evaluation.accuracy != null,
);
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
          Read-only view of the trained model, its inputs, provenance, and
          held-out performance.
        </p>
      </div>
    </header>

    <div v-if="error" class="error-banner" role="alert">
      {{ error }}
    </div>

    <section v-if="isLoading && !modelState" class="content-card loading-card">
      Loading model registry…
    </section>

    <div
      v-if="isStateLoading && modelState"
      class="state-loading"
      aria-live="polite"
    >
      Refreshing selected model state…
    </div>

    <template v-else-if="modelState">
      <section class="hero-card">
        <div>
          <div class="model-kicker">
            {{ modelState.algorithm }}
          </div>

          <div class="model-title-row">
            <h2>{{ modelState.name }}</h2>
            <span class="version-badge"> v{{ modelState.version }} </span>
          </div>

          <p class="model-caption">
            Trained from job #{{ modelState.training.job_id }} · created
            {{ formatDate(modelState.created_at) }}
          </p>
        </div>

        <span class="state-badge" :class="{ active: modelState.is_active }">
          {{ statusLabel }}
        </span>
      </section>

      <section class="summary-grid">
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
              <h2>Model & Training Provenance</h2>
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
            <span>Train / test</span>
            <strong>
              {{ modelState.training.train_count }}
              /
              {{ modelState.training.test_count }}
            </strong>
          </div>

          <div>
            <span>Split strategy</span>
            <strong>{{ modelState.training.split_strategy }}</strong>
          </div>

          <div>
            <span>Random seed</span>
            <strong>{{ modelState.training.random_seed }}</strong>
          </div>

          <div>
            <span>Completed</span>
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
                Features actually stored on the training run and used by the
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

      <section class="content-card">
        <div class="section-header">
          <div class="section-title-row">
            <div class="section-marker"></div>

            <div>
              <h2>Evaluation</h2>
              <p>Held-out performance generated during the training run.</p>
            </div>
          </div>

          <span class="section-badge" :class="{ ready: evaluationAvailable }">
            {{ evaluationAvailable ? "AVAILABLE" : "NOT AVAILABLE" }}
          </span>
        </div>

        <ModelEvaluationState
          v-if="evaluationAvailable"
          :evaluation="modelState.evaluation"
        />

        <div v-else class="empty-detail">
          A valid held-out evaluation is not available for this model version.
        </div>
      </section>

      <section
        v-if="modelState.feature_warnings.length"
        class="content-card warning-card"
      >
        <div class="section-header">
          <div class="section-title-row">
            <div class="section-marker"></div>

            <div>
              <h2>Validation & Feature Warnings</h2>
              <p>Scientific caveats recorded while producing this model.</p>
            </div>
          </div>
        </div>

        <div class="warning-list">
          <div
            v-for="warning in modelState.feature_warnings"
            :key="warning"
            class="warning-item"
          >
            {{ warning }}
          </div>
        </div>
      </section>
    </template>

    <section class="content-card registry-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker"></div>

          <div>
            <h2>Model Registry</h2>
            <p>Select a version to inspect its collective state.</p>
          </div>
        </div>

        <span class="section-badge"> {{ models.length }} VERSIONS </span>
      </div>

      <ModelRegistryTable
        :models="models"
        :selected-model-id="selectedModelId"
        @select="selectModel"
      />
    </section>
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
  margin: 0;
  color: var(--vf-muted);
  font-size: 13px;
}

.error-banner {
  margin-bottom: 18px;
  padding: 11px 13px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 11px;
}

.loading-card {
  padding: 26px;
  color: var(--vf-muted);
  font-size: 12px;
}

.state-loading {
  margin: 0 0 14px;
  padding: 9px 12px;
  border: 1px solid var(--vf-border-light);
  border-radius: 8px;
  background: #fff;
  color: var(--vf-muted);
  font-size: 10px;
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

.model-kicker {
  color: var(--vf-orange);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.model-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 5px;
}

.model-title-row h2 {
  margin: 0;
  color: var(--vf-dark);
  font-size: 21px;
}

.version-badge,
.section-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(249, 115, 22, 0.08);
  color: var(--vf-orange);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.model-caption {
  margin: 6px 0 0;
  color: var(--vf-muted);
  font-size: 11px;
}

.state-badge {
  display: inline-flex;
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}

.summary-card {
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
}

.content-card {
  margin-bottom: 18px;
  border: 1px solid var(--vf-border-light);
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
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
}

.section-badge.ready {
  background: #f0fdf4;
  color: #15803d;
}

.provenance-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}

.provenance-grid > div {
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
  overflow-wrap: anywhere;
}

.empty-detail {
  padding: 22px;
  color: var(--vf-muted);
  font-size: 11px;
}

.warning-card {
  border-color: #fed7aa;
}

.warning-list {
  padding: 18px 20px;
}

.warning-item {
  padding: 10px 12px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 11px;
}

.warning-item + .warning-item {
  margin-top: 8px;
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .provenance-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .provenance-grid > div:nth-child(4n) {
    border-right: 1px solid var(--vf-border-light);
  }

  .provenance-grid > div:nth-child(2n) {
    border-right: 0;
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

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .provenance-grid {
    grid-template-columns: 1fr;
  }

  .provenance-grid > div {
    border-right: 0;
  }

  .provenance-grid > div:last-child {
    border-bottom: 0;
  }

  .section-header {
    align-items: flex-start;
  }
}
</style>
