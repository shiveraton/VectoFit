<script setup lang="ts">
import { useTraining } from "../../hooks/useTraining";
import { computed, ref } from "vue";
import SummaryCard from "../../components/datasets/SummaryCard.vue";
import TrainingModal from "../../components/training/TrainingModal.vue";
import TrainingConfigGrid from "../../components/training/TrainingConfigGrid.vue";
import TrainingEmptyState from "../../components/training/TrainingEmptyState.vue";
import TrainingWorkflow from "../../components/training/TrainingWorkflow.vue";

interface Props {
  eyebrowText?: string;
  pageTitle?: string;
  pageDescription?: string;
  actionButtonText?: string;
}

withDefaults(defineProps<Props>(), {
  eyebrowText: "VECTOFIT MODEL TRAINING",
  pageTitle: "Training",
  pageDescription:
    "Configure and monitor machine learning experiments for squat movement classification.",
  actionButtonText: "New Training Run",
});

const emit = defineEmits<{
  (e: "new-run"): void;
  (e: "start-training"): void;
  (e: "job-started", jobId: string): void;
}>();

const {
  selectedDataset,
  selectedTaskId,
  tasks,
  features,
  algorithm,
  workflowSteps,
  summaryCards,
  configSummaryText,
  toggleFeature,
  selectTask,
} = useTraining();

const isModalOpen = ref(false);

const activeDatasetIds = computed(() => {
  if (!selectedDataset.value) return [];

  const dataset = selectedDataset.value as unknown as Record<string, any>;
  const id = typeof dataset === "object" ? dataset.id : dataset;
  return id ? [id] : [];
});

const handleStartTraining = () => {
  isModalOpen.value = true;
  emit("start-training");
};

const handleNewRun = () => {
  isModalOpen.value = true;
  emit("new-run");
};

const handleJobStarted = (jobData: { job_id: string }) => {
  emit("job-started", jobData.job_id);
};
</script>

<template>
  <div class="training-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          {{ eyebrowText }}
        </div>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageDescription }}</p>
      </div>

      <button class="primary-button" @click="handleNewRun">
        <span class="button-icon">+</span> {{ actionButtonText }}
      </button>
    </header>

    <section class="summary-grid">
      <SummaryCard
        v-for="card in summaryCards"
        :key="card.label"
        v-bind="card"
      />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <div>
              <h2>Training Configuration</h2>
              <p>
                Define the dataset, target and algorithm for a training
                experiment.
              </p>
            </div>
          </div>
        </div>
        <span class="status-badge">
          {{ selectedDataset ? "CONFIGURED" : "NOT CONFIGURED" }}
        </span>
      </div>

      <TrainingConfigGrid
        :selected-dataset="selectedDataset"
        :selected-task-id="selectedTaskId"
        :tasks="tasks"
        :features="features"
        :algorithm="algorithm"
        :summary-text="configSummaryText"
        @select-task="selectTask"
        @toggle-feature="toggleFeature"
        @start-training="handleStartTraining"
      />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <div>
              <h2>Training Runs</h2>
              <p>Previous model experiments and their evaluation status.</p>
            </div>
          </div>
        </div>
        <span class="status-badge">NO RUNS</span>
      </div>

      <TrainingEmptyState @configure="handleNewRun" />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <div>
              <h2>Training Workflow</h2>
              <p>The intended lifecycle of a VectoFit model experiment.</p>
            </div>
          </div>
        </div>
      </div>

      <TrainingWorkflow :steps="workflowSteps" />
    </section>

    <TrainingModal
      :is-open="isModalOpen"
      :dataset-ids="activeDatasetIds"
      @close="isModalOpen = false"
      @job-started="handleJobStarted"
    />
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
  margin-bottom: 28px;
}

.page-heading {
  display: flex;
  flex-direction: column;
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
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
  margin: 5px 0 0 12px;
  color: var(--vf-light-muted);
  font-size: 11px;
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 700px) {
  .training-page {
    padding: 20px;
  }
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 18px;
  }
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
