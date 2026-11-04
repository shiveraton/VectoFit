
<script setup lang="ts">
import { onMounted, ref } from "vue";
import client from "../../config/client";
import { useRouter } from "vue-router";

interface AnnotationDataset {
  id: number;
  name: string;
}

const router = useRouter();

const datasets = ref<AnnotationDataset[]>([]);
const error = ref<string | null>(null);
const isLoading = ref(true);

const fetchDatasets = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    const response = await client.get<AnnotationDataset[]>(
      "/datasets/annotation-datasets/",
    );

    datasets.value = response.data;
  } catch {
    error.value = "Unable to load annotation datasets.";
  } finally {
    isLoading.value = false;
  }
};

const openDataset = (id: number) => {
  router.push(`/annotator/${id}`);
};

onMounted(fetchDatasets);
</script>

<template>
  <div class="annotator-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          DATASET ANNOTATION
        </div>

        <h1>Choose a Dataset</h1>

        <p>
          Select a shared dataset to review and annotate its eligible samples.
        </p>
      </div>

      <button
        class="secondary-button"
        :disabled="isLoading"
        @click="fetchDatasets"
      >
        <span class="button-icon">↻</span>
        Refresh
      </button>
    </header>

    <section class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker"></div>

          <div>
            <h2>Available Datasets</h2>
            <p>
              Choose a dataset to begin the annotation process.
            </p>
          </div>
        </div>

        <span class="status-badge">
          {{ datasets.length }} DATASETS
        </span>
      </div>

      <div class="dataset-list">
        <div v-if="isLoading" class="empty-state">
          <div class="loading-spinner"></div>
          <p>Loading annotation datasets...</p>
        </div>

        <div v-else-if="error" class="empty-state error-state">
          <div class="empty-icon">!</div>
          <h3>Unable to Load Datasets</h3>
          <p>{{ error }}</p>

          <button class="secondary-button" @click="fetchDatasets">
            Try Again
          </button>
        </div>

        <div v-else-if="datasets.length === 0" class="empty-state">
          <div class="empty-icon">▤</div>
          <h3>No Annotation Datasets</h3>
          <p>
            There are currently no shared datasets available for annotation.
            Please check again later.
          </p>
        </div>

        <div v-else class="dataset-grid">
          <button
            v-for="dataset in datasets"
            :key="dataset.id"
            type="button"
            class="dataset-card"
            @click="openDataset(dataset.id)"
          >
            <div class="dataset-icon">
              <span>▤</span>
            </div>

            <div class="dataset-info">
              <span class="dataset-label">
                DATASET #{{ dataset.id }}
              </span>

              <h3>{{ dataset.name }}</h3>

              <p>Open dataset for annotation</p>
            </div>

            <span class="dataset-arrow">→</span>
          </button>
        </div>
      </div>

      <div v-if="!isLoading && !error && datasets.length > 0"
        class="card-footer"
      >
        Showing {{ datasets.length }} available annotation
        {{ datasets.length === 1 ? "dataset" : "datasets" }}.
      </div>
    </section>
  </div>
</template>

<style scoped>
.annotator-page {
  width: 100%;
  color: var(--vf-text);
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.page-heading h1 {
  margin: 10px 0 7px;
  color: var(--vf-dark);
  font-size: 26px;
  font-weight: 750;
  letter-spacing: -0.04em;
}

.page-heading > p {
  margin: 0;
  color: var(--vf-muted);
  font-size: 13px;
  line-height: 1.6;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--vf-orange-dark);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.eyebrow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--vf-orange);
}

/* Content Card */
.content-card {
  margin-bottom: 20px;
  overflow: hidden;
  background: var(--vf-surface);
  border: 1px solid var(--vf-border);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(24, 24, 27, 0.025);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid var(--vf-border-light);
}

.section-title-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.section-marker {
  width: 4px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 4px;
  background: var(--vf-gradient);
}

.section-title-row h2 {
  margin: 0 0 5px;
  color: var(--vf-dark);
  font-size: 14px;
  font-weight: 700;
}

.section-title-row p {
  margin: 0;
  color: var(--vf-muted);
  font-size: 11px;
}

.status-badge {
  padding: 5px 9px;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 5px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.07em;
  white-space: nowrap;
}

.dataset-list {
  min-height: 190px;
  padding: 20px;
}

.dataset-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.dataset-card {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  padding: 17px;
  text-align: left;
  background: #fff;
  border: 1px solid var(--vf-border);
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.dataset-card:hover {
  border-color: #fdba74;
  background: #fffaf5;
  box-shadow: 0 3px 10px rgba(249, 115, 22, 0.07);
  transform: translateY(-2px);
}

.dataset-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 43px;
  height: 43px;
  flex-shrink: 0;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 9px;
  font-size: 21px;
}

.dataset-info {
  flex: 1;
  min-width: 0;
}

.dataset-label {
  color: var(--vf-light-muted);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.dataset-info h3 {
  margin: 5px 0;
  color: var(--vf-dark);
  font-size: 13px;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.dataset-info p {
  margin: 0;
  color: var(--vf-muted);
  font-size: 10px;
}

.dataset-arrow {
  color: var(--vf-orange);
  font-size: 19px;
  transition: transform 0.18s ease;
}

.dataset-card:hover .dataset-arrow {
  transform: translateX(4px);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 190px;
  padding: 25px;
  text-align: center;
}

.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  margin-bottom: 13px;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 12px;
  font-size: 22px;
  font-weight: 700;
}

.empty-state h3 {
  margin: 0 0 6px;
  color: var(--vf-dark);
  font-size: 14px;
  font-weight: 700;
}

.empty-state p {
  max-width: 380px;
  margin: 0 0 15px;
  color: var(--vf-muted);
  font-size: 11px;
  line-height: 1.7;
}

.error-state .empty-icon {
  color: #b42318;
  background: var(--vf-red-soft);
  border-color: #fecaca;
}

.loading-spinner {
  width: 27px;
  height: 27px;
  margin-bottom: 13px;
  border: 3px solid var(--vf-border);
  border-top-color: var(--vf-orange);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.card-footer {
  padding: 12px 20px;
  color: var(--vf-light-muted);
  background: #fafafa;
  border-top: 1px solid var(--vf-border-light);
  font-size: 10px;
}

.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 14px;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
  white-space: nowrap;
}

.secondary-button:hover:not(:disabled) {
  background: #ffedd5;
  border-color: #fdba74;
}

.secondary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.button-icon {
  font-size: 16px;
  line-height: 1;
}

@media (max-width: 900px) {
  .dataset-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .section-header {
    align-items: flex-start;
  }

  .annotator-page {
    min-width: 0;
  }
}
</style>
