<template>
  <div class="page-header">
    <h1>Annotation Progress</h1>
  </div>

  <div v-if="isLoading" class="loading">Loading progress...</div>

  <div v-else-if="error" class="error">{{ error }}</div>

  <template v-else>
    <div class="progress-summary">
      <div class="progress-card">
        <div class="progress-icon">
          <svg viewBox="0 0 24 24" color="#15803d">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 9.5c-1.38 0-2.5 1.12-2.5 2.5s1.12 2.5 2.5 2.5 2.5-1.12 2.5-2.5S13.38 11.5 12 11.5zm0 5c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3S14.66 14 13 14z"/>
          </svg>
        </div>
        <div class="progress-info">
          <div class="progress-row">
            <span>Total Samples</span>
            <strong>{{ totalSamples }}</span>
          </div>
          <div class="progress-row">
            <span>Completed</span>
            <strong>{{ completedSamples }}</strong>
          </div>
          <div class="progress-row">
            <span>Remaining</span>
            <strong>{{ remainingSamples }}</strong>
          </div>
        </div>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: progressPercentage + '%' }"
          ></div>
        </div>
        <p class="progress-text">
          {{ progressPercentage }}% complete
        </p>
      </div>
    </div>

    <section class="datasets-progress">
      <h2>Per-Dataset Progress</h2>
      <div v-if="datasetsProgress.length === 0">
        <p>No dataset progress data available.</p>
      </div>
      <template v-else>
        <div class="dataset-progress-item" v-for="progress in datasetsProgress" :key="progress.datasetId">
          <div class="dataset-info">
            <strong>{{ progress.datasetName }}</strong>
            <span class="dataset-status" :class="progress.statusClass">
              {{ progress.statusLabel }}
            </span>
          </div>
          <div class="progress-details">
            <span>{{ progress.completed }} / {{ progress.total }}</span>
            <progress :max="progress.total" :value="progress.completed" class="native-progress"></progress>
          </div>
        </div>
      </template>
    </section>
  </template>

<script setup lang="ts">
import { computed, onMounted, watch, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAnnotationProgress } from "../../hooks/useAnnotationProgress";

const router = useRouter();
const route = useRoute();
const { loadProgress, totalSamples, completedSamples, remainingSamples, progressPercentage, datasetsProgress } = useAnnotationProgress();

onMounted(() => {
  loadProgress();
});
</script>

<style scoped>
.page-header {
  text-align: center;
  padding: 24px 0;
  border-bottom: 1px solid #e8edf3;
}

.progress-summary {
  max-width: 600px;
  margin: 0 auto;
  padding: 32px 0;
}

.progress-card {
  background: #ffffff;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  padding: 32px 24px;
  text-align: center;
}

.progress-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  color: #15803d;
}

.progress-info {
  text-align: center;
}

.progress-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
  color: #64748b;
}

.progress-row strong {
  color: #172033;
  font-weight: 600;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin: 16px 0;
}

.progress-fill {
  height: 100%;
  background: #15803d;
  width: 0%;
  transition: width 0.5s ease;
}

.progress-text {
  text-align: center;
  margin-top: 8px;
  font-size: 14px;
  color: #64748b;
}

.datasets-progress {
  padding: 24px 0;
}

.dataset-progress-item {
  display: flex;
  align-items: start;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #edf1f5;
}

.dataset-info {
  flex: 1;
}

.dataset-status {
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  margin-left: 8px;
}

.native-progress {
  width: 100%;
  height: 8px;
  margin-top: 4px;
}
</style>