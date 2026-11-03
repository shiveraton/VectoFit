<template>
  <div class="page-header">
    <h1>Available Datasets</h1>
  </div>

  <div v-if="isLoading" class="loading">Loading datasets...</div>

  <div v-else-if="error" class="error">{{ error }}</div>

  <template v-else>
    <p v-if="datasets.length === 0">
      No datasets assigned. Contact your administrator.
    </template>

    <template v-else>
      <div class="datasets-grid">
        <dataset-card-annotator
          v-for="dataset in datasets"
          :key="dataset.id"
          :dataset="dataset"
          @annotate=" $router.push('/annotator/datasets/' + dataset.id + '/annotate')"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAnnotatorDatasets } from "../../hooks/useAnnotatorDatasets";
import DatasetCardAnnotator from "../../components/datasets/DatasetCardAnnotator.vue";

const router = useRouter();
const route = useRoute();

const {
  datasets,
  isLoading,
  error,
  fetchDatasets,
  refetchDatasets,
} = useAnnotatorDatasets();

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

.datasets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  padding: 24px 0;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #8a96a8;
}
</style>