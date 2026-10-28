<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import SummaryCard from "../../components/datasets/SummaryCard.vue";
import TrainingConfiguration from "../../components/training/configuration/TrainingConfiguration.vue";
import TrainingResult from "../../components/training/results/TrainingResult.vue";
import TrainingWorkflow from "../../components/training/TrainingWorkflow.vue";
import { useTraining } from "../../hooks/useTraining";

const configurationSection = ref<HTMLElement | null>(null);

const {
  trainingJobs,
  features,
  algorithms,
  workflowSteps,
  selectedDatasets,
  selectedDatasetIds,
  selectedViewAngle,
  selectedAlgorithm,
  hyperparameters,
  testSize,
  randomSeed,
  summaryCards,
  configSummaryText,
  canStartTraining,
  isLoading,
  isTraining,
  error,
  toggleDataset,
  selectViewAngle,
  toggleFeature,
  selectAlgorithm,
  setHyperparameter,
  setTestSize,
  setRandomSeed,
  startTraining,
  availableDatasets,
  filteredDatasets,
} = useTraining();

const latestJob = computed(() => trainingJobs.value[0] ?? null);

const configurationStatus = computed(() => {
  if (isTraining.value) return "TRAINING";
  return canStartTraining.value ? "READY" : "INCOMPLETE";
});

const scrollToConfiguration = () => {
  configurationSection.value?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
};

const handleStartTraining = async () => {
  await startTraining();
};
</script>

<template>
  <div class="training-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot" aria-hidden="true"></span>
          VECTOFIT MODEL TRAINING
        </div>
        <h1>Training</h1>
        <p>
          Configure, train, and inspect VectoFit machine learning experiments.
        </p>
      </div>

      <button
        class="primary-button"
        type="button"
        @click="scrollToConfiguration"
      >
        <span class="button-icon" aria-hidden="true">+</span>
        New Training Run
      </button>
    </header>

    <section class="summary-grid" aria-label="Training summary">
      <SummaryCard
        v-for="card in summaryCards"
        :key="card.label"
        v-bind="card"
      />
    </section>

    <section ref="configurationSection" class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker" aria-hidden="true"></div>
          <div>
            <h2>Training Configuration</h2>
            <p>
              Define the datasets, camera view, features, algorithm, and
              experiment parameters.
            </p>
          </div>
        </div>

        <span
          :class="[
            'status-badge',
            {
              ready: configurationStatus === 'READY',
              running: configurationStatus === 'TRAINING',
            },
          ]"
        >
          {{ configurationStatus }}
        </span>
      </div>

      <div v-if="error" class="error-banner" role="alert">
        {{ error }}
      </div>

      <div v-if="isLoading" class="loading-state" aria-live="polite">
        <span class="loading-dot" aria-hidden="true"></span>
        Loading training configuration...
      </div>

      <TrainingConfiguration
        v-else
        :available-datasets="availableDatasets"
        :filtered-datasets="filteredDatasets"
        :selected-dataset-ids="selectedDatasetIds"
        :selected-datasets="selectedDatasets"
        :selected-view-angle="selectedViewAngle"
        :features="features"
        :algorithms="algorithms"
        :selected-algorithm="selectedAlgorithm"
        :hyperparameters="hyperparameters"
        :test-size="testSize"
        :random-seed="randomSeed"
        :summary-text="configSummaryText"
        :can-start-training="canStartTraining"
        :is-training="isTraining"
        @toggle-dataset="toggleDataset"
        @select-view-angle="selectViewAngle"
        @toggle-feature="toggleFeature"
        @select-algorithm="selectAlgorithm"
        @set-hyperparameter="setHyperparameter"
        @set-test-size="setTestSize"
        @set-random-seed="setRandomSeed"
        @start-training="handleStartTraining"
      />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker" aria-hidden="true"></div>
          <div>
            <h2>Training Result</h2>
            <p>
              Evaluation results produced by the latest configured experiment.
            </p>
          </div>
        </div>

        <span
          v-if="latestJob"
          :class="[
            'status-badge',
            {
              ready: latestJob.status === 'COMPLETED',
              running:
                latestJob.status === 'RUNNING' ||
                latestJob.status === 'PENDING',
              failed: latestJob.status === 'FAILED',
            },
          ]"
        >
          {{ latestJob.status }}
        </span>
      </div>

      <TrainingResult :job="latestJob" />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker" aria-hidden="true"></div>
          <div>
            <h2>Training Workflow</h2>
            <p>The intended lifecycle of a VectoFit model experiment.</p>
          </div>
        </div>
      </div>

      <TrainingWorkflow :steps="workflowSteps" />
    </section>
  </div>
</template>

<style scoped>
.training-page {
  min-height: 100%;
  padding: 32px;
  background: var(--vf-background);
  font-family: "Segoe UI", Arial, sans-serif;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.page-heading {
  min-width: 0;
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
  flex-shrink: 0;
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 22px;
  border-bottom: 1px solid var(--vf-border-light);
}

.section-title-row {
  display: flex;
  align-items: flex-start;
  gap: 9px;
}

.section-marker {
  flex-shrink: 0;
  width: 3px;
  height: 17px;
  margin-top: 1px;
  border-radius: 4px;
  background: var(--vf-gradient);
}

.section-header h2 {
  margin: 0;
  color: var(--vf-dark);
  font-size: 15px;
  font-weight: 700;
}

.section-header p {
  margin: 5px 0 0;
  color: var(--vf-light-muted);
  font-size: 11px;
  line-height: 1.5;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  min-width: 78px;
  padding: 5px 9px;
  border-radius: 999px;
  color: var(--vf-muted);
  background: #f4f4f5;
  border: 1px solid var(--vf-border);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.status-badge.ready {
  color: #15803d;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.status-badge.running {
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border-color: #fed7aa;
}

.status-badge.failed {
  color: #b91c1c;
  background: var(--vf-red-soft);
  border-color: #fecaca;
}

.error-banner {
  margin: 18px 22px 0;
  padding: 11px 13px;
  color: #991b1b;
  background: var(--vf-red-soft);
  border: 1px solid #fecaca;
  border-radius: 8px;
  font-size: 11px;
  line-height: 1.5;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 26px 22px;
  color: var(--vf-muted);
  font-size: 12px;
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--vf-orange);
  animation: pulse 1s ease-in-out infinite;
}

.primary-button {
  white-space: nowrap;
}

.button-icon {
  font-size: 16px;
  font-weight: 400;
  line-height: 1;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.35;
  }
  50% {
    opacity: 1;
  }
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .training-page {
    padding: 20px;
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .section-header {
    align-items: flex-start;
  }
}
</style>
