<script setup lang="ts">
import { computed, ref } from "vue";
import type { TrainingJob } from "../../services/trainingService";

import SummaryCard from "../../components/datasets/SummaryCard.vue";
import TrainingConfiguration from "../../components/training/configuration/TrainingConfiguration.vue";
import TrainingResult from "../../components/training/results/TrainingResult.vue";
import { useTraining } from "../../hooks/useTraining";

const configurationSection = ref<HTMLElement | null>(null);

const {
  features,
  selectedDatasets,
  selectedDatasetIds,
  selectedViewAngle,
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
  setHyperparameter,
  setTestSize,
  setRandomSeed,
  startTraining,
  availableDatasets,
  filteredDatasets,
  trainingJobs,
  selectedJob,
  selectJob,
} = useTraining();

const handleStartTraining = async () => {
  const job = await startTraining();
  if (job) {
    selectJob(job.id);
  }
};

const formatDate = (dateStr: string) => new Date(dateStr).toLocaleString();

const selectedJobId = computed<number | null>({
  get: () => selectedJob.value?.id ?? null,
  set: (jobId) => {
    if (jobId !== null) {
      selectJob(jobId);
    }
  },
});

const latestJob = computed<TrainingJob | null>(() => selectedJob.value);

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
          Train and inspect frontal-plane knee-alignment models using FPPA v2.
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

    <section class="content-card history-card" aria-label="FPPA training history">
  <div class="section-header">
    <h2>FPPA Training History</h2>
    <select v-if="trainingJobs.length" v-model="selectedJobId" class="job-select" aria-label="Select an FPPA training run">
      <option v-for="job in trainingJobs" :key="job.id" :value="job.id">
        {{ job.id }} – {{ formatDate(job.created_at) }} – {{ job.status }}
      </option>
    </select>
  </div>
  <p v-if="!trainingJobs.length" class="history-empty">
    No FPPA v2 runs recorded yet. Start a run to create the first M1 model.
  </p>
</section>

      <section class="summary-grid" aria-label="FPPA training summary">
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
              Configure an FPPA v2 M1 training experiment for the frontal view.
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
        :hyperparameters="hyperparameters"
        :test-size="testSize"
        :random-seed="randomSeed"
        :summary-text="configSummaryText"
        :can-start-training="canStartTraining"
        :is-training="isTraining"
        @toggle-dataset="toggleDataset"
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
              Held-out evaluation for the selected FPPA v2 training run.
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

  </div>
</template>

<style scoped>

.history-card {
  margin-bottom: 20px;
}

.job-select {
  min-width: 280px;
  max-width: 100%;
  padding: 9px 11px;
  border: 1px solid var(--vf-border);
  border-radius: 8px;
  background: #fff;
  color: var(--vf-text);
  font: inherit;
  font-size: 13px;
}

.history-empty {
  margin: 0;
  padding: 18px 22px;
  color: var(--vf-muted);
  font-size: 13px;
  line-height: 1.55;
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

@keyframes pulse {
  0%,
  100% {
    opacity: 0.35;
  }
  50% {
    opacity: 1;
  }
}

@media (max-width: 700px) {

.job-select {
    width: 100%;
    min-width: 0;
  }

}

</style>
