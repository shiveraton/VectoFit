<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useDatasets } from "../../hooks/useDatasets";
import SummaryCard from "../../components/datasets/SummaryCard.vue";
import DatasetEmptyState from "../../components/datasets/DatasetEmptyState.vue";
import StructureGrid from "../../components/datasets/StructureGrid.vue";
import CreateDatasetModal from "../../components/datasets/CreateDatasetModal.vue";

const {
  datasets = ref([]),
  isLoading,
  isCreating,
  isModalOpen,
  datasetForm,
  fetchDatasets,
  openCreateModal,
  closeCreateModal,
  handleCreateDataset,
} = useDatasets();

onMounted(() => {
  fetchDatasets();
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

      <button class="primary-button" @click="() => openCreateModal()">
        <span class="button-icon">+</span>
        Create Dataset
      </button>
    </header>

    <section class="summary-grid">
      <SummaryCard
        label="Total Samples"
        value="0"
        description="Completed squat repetitions"
        icon="∑"
        variant="samples"
      />
      <SummaryCard
        label="Correct Reps"
        value="0"
        description="Labeled as correct"
        icon="✓"
        variant="correct"
      />
      <SummaryCard
        label="Incorrect Reps"
        value="0"
        description="Labeled as incorrect"
        icon="!"
        variant="incorrect"
      />
      <SummaryCard
        label="Dataset Versions"
        value="0"
        description="Available versions"
        icon="↻"
        variant="version"
      />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <h2>Datasets</h2>
          </div>
        </div>
      </div>

      <DatasetEmptyState
        v-if="datasets.length === 0 && !isLoading"
        @action="openCreateModal"
      />

      <div v-else-if="isLoading" class="loading-state">Loading datasets...</div>

      <div v-else class="dataset-list">
        <div v-for="dataset in datasets" :key="dataset.id" class="dataset-item">
          <h4>{{ dataset.name }}</h4>
          <p>Status: {{ dataset.status }}</p>
          <video v-if="dataset.video_file" controls width="300">
            <source
              :src="'http://192.168.1.101:8000' + dataset.video_file"
              type="video/mp4"
            />
          </video>
        </div>
      </div>
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <h2>Dataset Structure</h2>
          </div>
          <p>Each completed squat repetition represents one sample.</p>
        </div>
      </div>

      <StructureGrid />
    </section>

    <CreateDatasetModal
      :is-open="isModalOpen"
      :is-submitting="isCreating"
      :form="datasetForm"
      @close="() => closeCreateModal()"
      @submit="() => handleCreateDataset()"
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
  padding: 32px;
  text-align: center;
  font-size: 12px;
  color: var(--vf-muted, #71717a);
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
</style>
