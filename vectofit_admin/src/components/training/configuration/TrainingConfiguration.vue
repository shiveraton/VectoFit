<script setup lang="ts">
import type { Dataset } from "../../../services/datasetService";
import type {
  AlgorithmOption,
  FeatureOption,
} from "../../../services/trainingService";

import AlgorithmSelector from "./AlgorithmSelector.vue";
import DatasetSelector from "./DatasetSelector.vue";
import FeatureSelector from "./FeatureSelector.vue";
import HyperparameterPanel from "./HyperparameterPanel.vue";
import ViewAngleSelector from "./ViewAngleSelector.vue";

type ViewAngle = "diagonal" | "frontal" | "sagittal";
type DatasetId = number;

interface Props {
  availableDatasets: Dataset[];
  filteredDatasets: Dataset[];
  selectedDatasetIds: DatasetId[];
  selectedDatasets: Dataset[];
  selectedViewAngle: ViewAngle | null;
  features: FeatureOption[];
  algorithms: AlgorithmOption[];
  selectedAlgorithm: AlgorithmOption | null;
  hyperparameters: Record<string, unknown>;
  testSize: number;
  randomSeed: number;
  summaryText: string;
  canStartTraining: boolean;
  isTraining: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  (event: "toggle-dataset", id: DatasetId): void;
  (event: "select-view-angle", angle: ViewAngle): void;
  (event: "toggle-feature", id: string): void;
  (event: "select-algorithm", id: string): void;
  (event: "set-hyperparameter", key: string, value: number): void;
  (event: "set-test-size", value: number): void;
  (event: "set-random-seed", value: number): void;
  (event: "start-training"): void;
}>();
</script>

<template>
  <div class="configuration-grid">
    <DatasetSelector
      :available-datasets="availableDatasets"
      :filtered-datasets="filteredDatasets"
      :selected-dataset-ids="selectedDatasetIds"
      :selected-datasets="selectedDatasets"
      :selected-view-angle="selectedViewAngle"
      @toggle-dataset="emit('toggle-dataset', $event)"
    />

    <ViewAngleSelector
      :selected-view-angle="selectedViewAngle"
      @select-view-angle="emit('select-view-angle', $event)"
    />

    <FeatureSelector
      :features="features"
      @toggle-feature="emit('toggle-feature', $event)"
    />

    <AlgorithmSelector
      :algorithms="algorithms"
      :selected-algorithm="selectedAlgorithm"
      @select-algorithm="emit('select-algorithm', $event)"
    />

    <HyperparameterPanel
      :hyperparameters="hyperparameters"
      :test-size="testSize"
      :random-seed="randomSeed"
      @set-hyperparameter="emit('set-hyperparameter', $event.key, $event.value)"
      @set-test-size="emit('set-test-size', $event)"
      @set-random-seed="emit('set-random-seed', $event)"
    />
  </div>

  <footer class="configuration-footer">
    <div class="summary-copy">
      <span class="footer-label">Configuration Summary</span>
      <strong>{{ summaryText }}</strong>
    </div>

    <button
      class="primary-button"
      type="button"
      :disabled="!canStartTraining || isTraining"
      @click="emit('start-training')"
    >
      <span v-if="isTraining" class="button-spinner" aria-hidden="true"></span>
      {{ isTraining ? "Training..." : "Start Training" }}
    </button>
  </footer>
</template>

<style scoped>
.configuration-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.configuration-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px 22px;
  background: #fcfcfc;
  border-top: 1px solid var(--vf-border-light);
}

.summary-copy {
  min-width: 0;
}

.footer-label {
  display: block;
  margin-bottom: 4px;
  color: var(--vf-light-muted);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-copy strong {
  display: block;
  color: var(--vf-text);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.45;
}

.primary-button {
  min-width: 132px;
}

.button-spinner {
  width: 11px;
  height: 11px;
  border: 1.5px solid rgba(255, 255, 255, 0.55);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 800px) {
  .configuration-grid {
    grid-template-columns: 1fr;
  }

  .configuration-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .primary-button {
    width: 100%;
  }
}
</style>
