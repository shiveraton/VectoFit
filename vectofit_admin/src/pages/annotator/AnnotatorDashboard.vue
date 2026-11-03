<template>
  <div class="page-header">
    <h1>Annotator Dashboard</h1>
  </div>

  <div class="dashboard-grid">
    <div class="card">
      <div class="card-icon">
        <svg viewBox="0 0 24 24" color="#15803d">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 9.5c-1.38 0-2.5 1.12-2.5 2.5s1.12 2.5 2.5 2.5 2.5-1.12 2.5-2.5S13.38 11.5 12 11.5zm0 5c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3S14.66 14 13 14z"/>
        </svg>
      </div>
      <div class="card-info">
        <div class="card-title">Total Samples</div>
        <div class="card-value" id="total-samples">Loading...</div>
      </div>
    </div>

    <div class="card">
      <div class="card-icon">
        <svg viewBox="0 0 24 24" color="#15803d">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 9.5c-1.38 0-2.5 1.12-2.5 2.5s1.12 2.5 2.5 2.5 2.5-1.12 2.5-2.5S13.38 11.5 12 11.5zm0 5c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3S14.66 14 13 14z"/>
        </svg>
      </div>
      <div class="card-info">
        <div class="card-title">Completed</div>
        <div class="card-value" id="completed-samples">0</div>
      </div>
    </div>

    <div class="card">
      <div class="card-icon">
        <svg viewBox="0 0 24 24" color="#15803d">
          <path d="M12 4v16M4 12h16"/>
        </svg>
      </div>
      <div class="card-info">
        <div class="card-title">Remaining</div>
        <div class="card-value" id="remaining-samples">0</div>
      </div>
    </div>
  </div>

  <section class="datasets-section">
    <h2>Available Datasets</h2>
    <div v-if="isLoading" class="loading">Loading datasets...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else-if="datasets.length === 0">
      <p class="empty-state">No datasets assigned. Contact your administrator.</p>
    </template>
    <template v-else>
      <div class="datasets-grid">
        <dataset-card
          v-for="dataset in datasets"
          :key="dataset.id"
          :dataset="dataset"
          @annotate=" $router.push('/annotator/datasets/' + dataset.id + '/annotate')"
        />
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, watch, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAnnotatorDatasets } from "../../hooks/useAnnotatorDatasets";
import { useAnnotationProgress } from "../../hooks/useAnnotationProgress";

const router = useRouter();
const route = useRoute();

const {
  datasets,
  isLoading,
  error,
  fetchDatasets,
  refetchDatasets,
} = useAnnotatorDatasets();

const {
  totalSamples,
  completedSamples,
  remainingSamples,
  progressPercentage,
} = useAnnotationProgress();

onMounted(() => {
  fetchDatasets();
});

watch(fetchDatasets, () => {
  refetchDatasets();
});
</script>

<style scoped>
.page-header {
  text-align: center;
  padding: 24px 0;
  border-bottom: 1px solid #e8edf3;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  padding: 24px 0;
}

.card {
  background: #ffffff;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  padding: 24px;
  text-align: center;
  transition: transform 0.2s ease;
}

.card:hover {
  transform: translateY(-2px);
}

.card-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
  color: #15803d;
}

.card-info {
  text-align: center;
}

.card-title {
  font-size: 11px;
  color: #8a96a8;
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: 700;
  color: #172033;
}

.datasets-section {
  padding: 24px 0;
}

.datasets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #8a96a8;
}
</style>