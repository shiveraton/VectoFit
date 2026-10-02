<script setup lang="ts">
import { ref, computed } from "vue";
import { useEvaluation } from "../../hooks/useEvaluation";
import SummaryCard from "../../components/datasets/SummaryCard.vue";
import EvaluationModal from "../../components/evaluation/EvaluationModal.vue";
import EvaluationConfigGrid from "../../components/evaluation/EvaluationConfigGrid.vue";
import EvaluationEmptyState from "../../components/evaluation/EvaluationEmptyState.vue";
import EvaluationTable from "../../components/evaluation/EvaluationTable.vue";
import EvaluationWorkflow from "../../components/evaluation/EvaluationWorkflow.vue";

interface Props {
  eyebrowText?: string;
  pageTitle?: string;
  pageDescription?: string;
  actionButtonText?: string;
}

withDefaults(defineProps<Props>(), {
  eyebrowText: "VECTOFIT MODEL EVALUATION",
  pageTitle: "Evaluation",
  pageDescription:
    "Assess model predictions, posture scores, and biomechanical movement accuracy.",
  actionButtonText: "New Evaluation",
});

const emit = defineEmits<{
  (e: "new-evaluation"): void;
  (e: "start-evaluation"): void;
  (e: "evaluation-started", evaluationId: string): void;
}>();

const {
  selectedDataset,
  selectedModelId,
  models,
  metrics,
  evaluations,
  workflowSteps,
  summaryCards,
  configSummaryText,
  toggleMetric,
  selectModel,
} = useEvaluation();

const isModalOpen = ref(false);

const activeDatasetIds = computed(() => {
  if (!selectedDataset.value) return [];

  const dataset = selectedDataset.value as unknown as Record<string, any>;
  const id = typeof dataset === "object" ? dataset.id : dataset;
  return id ? [id] : [];
});

const hasEvaluations = computed(
  () => evaluations.value && evaluations.value.length > 0,
);

const handleStartEvaluation = () => {
  isModalOpen.value = true;
  emit("start-evaluation");
};

const handleNewEvaluation = () => {
  isModalOpen.value = true;
  emit("new-evaluation");
};

const handleEvaluationStarted = (data: { evaluation_id: string }) => {
  emit("evaluation-started", data.evaluation_id);
};
</script>

<template>
  <div class="evaluation-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          {{ eyebrowText }}
        </div>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageDescription }}</p>
      </div>

      <button class="primary-button" @click="handleNewEvaluation">
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
              <h2>Evaluation Configuration</h2>
              <p>
                Select target model, reference dataset, and benchmark metrics to
                evaluate.
              </p>
            </div>
          </div>
        </div>
        <span class="status-badge">
          {{ selectedDataset ? "CONFIGURED" : "NOT CONFIGURED" }}
        </span>
      </div>

      <EvaluationConfigGrid
        :selected-dataset="selectedDataset"
        :selected-model-id="selectedModelId"
        :models="models"
        :metrics="metrics"
        :summary-text="configSummaryText"
        @select-model="selectModel"
        @toggle-metric="toggleMetric"
        @start-evaluation="handleStartEvaluation"
      />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <div>
              <h2>Evaluation Results</h2>
              <p>Completed model evaluations and movement vector benchmarks.</p>
            </div>
          </div>
        </div>
        <span class="status-badge">
          {{ hasEvaluations ? `${evaluations.length} RECORDS` : "NO RECORDS" }}
        </span>
      </div>

      <EvaluationTable v-if="hasEvaluations" :evaluations="evaluations" />
      <EvaluationEmptyState v-else @configure="handleNewEvaluation" />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <div>
              <h2>Evaluation Workflow</h2>
              <p>
                Standard process for model validation and posture accuracy
                checking.
              </p>
            </div>
          </div>
        </div>
      </div>

      <EvaluationWorkflow :steps="workflowSteps" />
    </section>

    <EvaluationModal
      :is-open="isModalOpen"
      :dataset-ids="activeDatasetIds"
      @close="isModalOpen = false"
      @evaluation-started="handleEvaluationStarted"
    />
  </div>
</template>

<style scoped>
.evaluation-page {
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
  .evaluation-page {
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
