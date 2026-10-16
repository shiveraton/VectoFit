<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";

import { useDatasets } from "../../hooks/useDatasets";
import { useParticipants } from "../../hooks/useParticipants.ts";
import { type Dataset } from "../../services/datasetService";

import SummaryCard from "../../components/datasets/SummaryCard.vue";
import DatasetEmptyState from "../../components/datasets/DatasetEmptyState.vue";
import StructureGrid from "../../components/datasets/StructureGrid.vue";
import CreateDatasetModal from "../../components/datasets/CreateDatasetModal.vue";
import DatasetImportModal from "../../components/datasets/DatasetImportModal.vue";

const router = useRouter();

const {
  datasets,
  isLoading,
  isCreating,
  isModalOpen,
  datasetForm,
  errorMessage,
  successMessage,
  totalDatasets,
  totalSamples,
  usableDatasets,
  fetchDatasets,
  openCreateModal,
  closeCreateModal,
  handleCreateDataset,
  retryDataset,
} = useDatasets();

const { participants, fetchParticipants, createParticipant } =
  useParticipants();

const hasSamples = (dataset: Dataset) => dataset.sample_count > 0;

const hasUnlabelledSamples = (dataset: Dataset) =>
  dataset.sample_count > dataset.labelled_sample_count;

const isAnnotationReady = (dataset: Dataset) =>
  dataset.status === "READY" &&
  hasSamples(dataset) &&
  hasUnlabelledSamples(dataset);

const isFullyLabelled = (dataset: Dataset) =>
  hasSamples(dataset) && !hasUnlabelledSamples(dataset);

const openAnnotation = (datasetId: number) => {
  router.push(`/dataset/${datasetId}/annotate`);
};

const handleAddParticipant = async () => {
  const participant = await createParticipant();

  if (participant) {
    datasetForm.value.participant = participant.id;
    console.log(`Created participant ${participant.participant_code}`);
  }
};

const handleRetryDataset = async (datasetId: number) => {
  await retryDataset(datasetId);
};

const processingDatasetCount = computed(
  () =>
    datasets.value.filter((dataset) => dataset.status === "PROCESSING").length,
);

const isImportModalOpen = ref(false);

const openImportModal = () => {
  isImportModalOpen.value = true;
};

const handleBulkImported = async (datasetName: string, videoCount: number) => {
  successMessage.value =
    `Imported ${videoCount} video(s) into "${datasetName}". ` +
    "Video processing has been queued.";

  await fetchDatasets(true);
};

onMounted(async () => {
  await Promise.all([fetchParticipants(), fetchDatasets()]);
});
</script>

<template>
  <div class="dataset-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          VECTOFIT DATA PIPELINE
        </div>

        <h1>Datasets</h1>

        <p>Manage datasets used for VectoFit model training and evaluation.</p>
      </div>

      <div class="page-actions">
        <button class="secondary-button" type="button" @click="openCreateModal">
          Add Single Video
        </button>

        <button class="primary-button" type="button" @click="openImportModal">
          <span class="button-icon">↑</span>
          Import Dataset
        </button>
      </div>
    </header>

    <div v-if="successMessage" class="feedback-message success">
      {{ successMessage }}
    </div>

    <div v-if="errorMessage" class="feedback-message error">
      {{ errorMessage }}
    </div>

    <section class="summary-grid">
      <SummaryCard
        label="Datasets"
        :value="totalDatasets"
        description="Registered datasets"
        icon="D"
        variant="samples"
      />

      <SummaryCard
        label="Samples"
        :value="totalSamples"
        description="Completed squat repetitions"
        icon="Σ"
        variant="samples"
      />

      <SummaryCard
        label="Training Ready"
        :value="usableDatasets.length"
        description="Datasets with labelled samples"
        icon="✓"
        variant="correct"
      />

      <SummaryCard
        label="Processing"
        :value="processingDatasetCount"
        description="Currently being processed"
        icon="↻"
        variant="version"
      />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker"></div>

          <div>
            <h2>Datasets</h2>
            <p>Registered exercise data and preprocessing status.</p>
          </div>
        </div>
      </div>

      <DatasetEmptyState
        v-if="!isLoading && datasets.length === 0"
        @action="openCreateModal"
      />

      <div v-else-if="isLoading" class="loading-state" aria-live="polite">
        <span class="loading-dot" aria-hidden="true"></span>
        Loading datasets...
      </div>

      <div v-else class="dataset-table-wrapper">
        <table class="dataset-table">
          <thead>
            <tr>
              <th>Dataset</th>
              <th>Participant</th>
              <th>Exercise</th>
              <th>Purpose</th>
              <th>Samples</th>
              <th>Labelled</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="dataset in datasets" :key="dataset.id">
              <td>
                <div class="dataset-name">
                  <strong>{{ dataset.name }}</strong>
                  <span class="dataset-id">#{{ dataset.id }}</span>
                </div>
              </td>

              <td>
                <span v-if="dataset.participant" class="participant-value">
                  P-{{ dataset.participant }}
                </span>

                <span v-else class="muted-value"> Unassigned </span>
              </td>

              <td>
                <span class="exercise-value">
                  {{ dataset.exercise_type }}
                </span>
              </td>

              <td>
                {{ dataset.purpose }}
              </td>

              <td>
                <span class="sample-count">
                  {{ dataset.sample_count }}
                </span>
              </td>

              <td>
                <span class="labelled-count">
                  <strong>{{ dataset.labelled_sample_count }}</strong>
                  /
                  {{ dataset.sample_count }}
                </span>
              </td>

              <td>
                <span
                  class="status-badge"
                  :class="`status-${dataset.status.toLowerCase()}`"
                >
                  <span
                    v-if="dataset.status === 'PROCESSING'"
                    class="processing-indicator"
                  ></span>

                  {{ dataset.status }}
                </span>
              </td>

              <td>
                <div class="action-cell">
                  <button
                    v-if="isAnnotationReady(dataset)"
                    type="button"
                    class="action-button"
                    @click="openAnnotation(dataset.id)"
                  >
                    Annotate
                  </button>

                  <span
                    v-else-if="isFullyLabelled(dataset)"
                    class="action-complete"
                  >
                    Complete
                  </span>

                  <span
                    v-else-if="dataset.status === 'PROCESSING'"
                    class="processing-state"
                  >
                    <span class="processing-spinner"></span>
                    Processing...
                  </span>

                  <button
                    v-else-if="dataset.status === 'FAILED'"
                    type="button"
                    class="action-button retry-button"
                    @click="handleRetryDataset(dataset.id)"
                  >
                    Retry
                  </button>

                  <span
                    v-else-if="dataset.status === 'PENDING'"
                    class="muted-value"
                  >
                    Queued
                  </span>

                  <span v-else class="muted-value">—</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker"></div>

          <div>
            <h2>Dataset Structure</h2>
            <p>Each completed squat repetition represents one sample.</p>
          </div>
        </div>
      </div>

      <StructureGrid />
    </section>

    <CreateDatasetModal
      :is-open="isModalOpen"
      :is-submitting="isCreating"
      :form="datasetForm"
      :participants="participants"
      @create-participant="handleAddParticipant"
      @close="closeCreateModal"
      @submit="handleCreateDataset"
    />

    <DatasetImportModal
      :is-open="isImportModalOpen"
      @close="isImportModalOpen = false"
      @imported="handleBulkImported"
    />
  </div>
</template>

<style scoped>
.dataset-page {
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

.page-actions {
  display: flex;
  align-items: center;
  gap: 10px;
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

.primary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 16px;
  color: #ffffff;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  border: 1px solid transparent;
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 2px 5px rgba(239, 68, 68, 0.16);
  cursor: pointer;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.primary-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 5px 12px rgba(239, 68, 68, 0.22);
}

.button-icon {
  font-size: 18px;
  font-weight: 400;
  line-height: 1;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.content-card {
  margin-bottom: 20px;
  overflow: hidden;
  background: var(--vf-surface, #ffffff);
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(24, 24, 27, 0.025);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
}

.section-title-row {
  display: flex;
  align-items: center;
  gap: 9px;
}

.section-marker {
  width: 3px;
  height: 17px;
  border-radius: 4px;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
}

.section-header h2 {
  margin: 0;
  color: var(--vf-dark, #18181b);
  font-size: 15px;
  font-weight: 700;
}

.section-header p {
  margin: 5px 0 0 12px;
  color: var(--vf-light-muted, #a1a1aa);
  font-size: 11px;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 26px 22px;
  font-size: 12px;
  color: var(--vf-muted, #71717a);
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--vf-orange);
  animation: pulse 1s ease-in-out infinite;
}

.dataset-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.dataset-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.dataset-table th {
  padding: 12px 22px;
  color: var(--vf-light-muted, #a1a1aa);
  background: #fafafa;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-align: left;
  text-transform: uppercase;
}

.dataset-table td {
  padding: 15px 22px;
  color: var(--vf-dark, #18181b);
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  font-size: 12px;
  vertical-align: middle;
}

.dataset-table tbody tr:last-child td {
  border-bottom: none;
}

.dataset-table tbody tr {
  transition: background 0.15s ease;
}

.dataset-table tbody tr:hover {
  background: #fffaf7;
}

.dataset-name {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 180px;
}

.dataset-name strong {
  color: var(--vf-dark, #18181b);
  font-size: 12px;
  font-weight: 600;
}

.dataset-id {
  color: var(--vf-light-muted, #a1a1aa);
  font-size: 10px;
  font-weight: 500;
}

.participant-value {
  color: var(--vf-dark, #27272a);
  font-weight: 600;
}

.muted-value {
  color: var(--vf-light-muted, #a1a1aa);
}

.exercise-value {
  color: var(--vf-muted, #71717a);
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 11px;
}

.sample-count {
  color: var(--vf-dark, #18181b);
  font-weight: 600;
}

.labelled-count {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--vf-muted, #71717a);
  font-size: 11px;
}

.labelled-count strong {
  color: var(--vf-dark, #18181b);
  font-weight: 600;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 68px;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.status-badge.ready {
  color: #15803d;
  background: #f0fdf4;
}

.status-badge.processing {
  color: #c2410c;
  background: #fff7ed;
}

.status-badge.pending {
  color: #a16207;
  background: #fefce8;
}

.status-badge.failed {
  color: #dc2626;
  background: #fef2f2;
}

.empty-state {
  padding: 42px 24px;
  color: var(--vf-muted, #71717a);
  text-align: center;
  font-size: 12px;
}

.action-cell {
  display: flex;
  align-items: center;
  min-height: 30px;
}

.action-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 7px 11px;
  color: #ffffff;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  border: 1px solid transparent;
  border-radius: 6px;
  font-family: inherit;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    opacity 0.15s ease;
}

.action-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(239, 68, 68, 0.18);
}

.action-button:active {
  transform: translateY(0);
}

.action-complete {
  color: #15803d;
  font-size: 10px;
  font-weight: 700;
}

.processing-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--vf-muted, #71717a);
  font-size: 10px;
  font-weight: 600;
}

.processing-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: processing-pulse 1.2s ease-in-out infinite;
}

.processing-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: processing-spin 0.8s linear infinite;
}

.retry-button {
  min-width: 48px;
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

@keyframes processing-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1000px) {
  .dataset-table {
    min-width: 820px;
  }
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 700px) {
  .dataset-page {
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

@media (max-width: 700px) {
  .page-actions {
    width: 100%;
    flex-direction: column;
  }

  .page-actions button {
    width: 100%;
  }
}
</style>
