<script setup lang="ts">
import type {
  TrainingTask,
  FeatureOption,
  AlgorithmOption,
} from "../../services/trainingService";

interface Props {
  selectedDataset: string | null;
  selectedTaskId: string;
  tasks: TrainingTask[];
  features: FeatureOption[];
  algorithm: AlgorithmOption;
  summaryText: string;
  submitButtonText?: string;
  noDatasetText?: string;
}

withDefaults(defineProps<Props>(), {
  submitButtonText: "Start Training",
  noDatasetText: "No dataset selected",
});

const emit = defineEmits<{
  (e: "select-task", id: string): void;
  (e: "toggle-feature", id: string): void;
  (e: "start-training"): void;
}>();
</script>

<template>
  <div class="configuration-grid">
    <div class="configuration-section">
      <div class="configuration-label">
        <span class="configuration-number">01</span>
        <div>
          <strong>Dataset</strong>
          <span>Select the data used for model training.</span>
        </div>
      </div>

      <div class="select-placeholder">
        <div>
          <strong>{{ selectedDataset || noDatasetText }}</strong>
          <span>Create or select a prepared dataset.</span>
        </div>
        <span class="select-arrow">⌄</span>
      </div>
    </div>

    <div class="configuration-section">
      <div class="configuration-label">
        <span class="configuration-number">02</span>
        <div>
          <strong>Training Task</strong>
          <span>Choose the classification objective.</span>
        </div>
      </div>

      <div class="task-options">
        <div
          v-for="task in tasks"
          :key="task.id"
          :class="['task-option', { selected: selectedTaskId === task.id }]"
          @click="emit('select-task', task.id)"
        >
          <div class="task-option-icon">{{ task.code }}</div>
          <div>
            <strong>{{ task.title }}</strong>
            <span>{{ task.description }}</span>
          </div>
          <span class="option-indicator"></span>
        </div>
      </div>
    </div>

    <div class="configuration-section">
      <div class="configuration-label">
        <span class="configuration-number">03</span>
        <div>
          <strong>Features</strong>
          <span>Select the measurements supplied to the model.</span>
        </div>
      </div>

      <div class="feature-selection">
        <label
          v-for="feature in features"
          :key="feature.id"
          :class="['feature-check', { selected: feature.selected }]"
          @click="emit('toggle-feature', feature.id)"
        >
          <span class="check-box">{{ feature.selected ? "✓" : "" }}</span>
          <span>{{ feature.name }}</span>
        </label>
      </div>
    </div>

    <div class="configuration-section">
      <div class="configuration-label">
        <span class="configuration-number">04</span>
        <div>
          <strong>Algorithm</strong>
          <span>Select the machine learning model.</span>
        </div>
      </div>

      <div v-if="algorithm" class="algorithm-card">
        <div class="algorithm-icon">{{ algorithm.code }}</div>
        <div>
          <strong>{{ algorithm.name }}</strong>
          <span>{{ algorithm.description }}</span>
        </div>
        <span class="algorithm-status">Selected</span>
      </div>
    </div>
  </div>

  <div class="configuration-footer">
    <div>
      <span class="footer-label">Configuration Summary</span>
      <strong>{{ summaryText }}</strong>
    </div>

    <button
      :class="selectedDataset ? 'primary-button' : 'disabled-button'"
      :disabled="!selectedDataset"
      @click="emit('start-training')"
    >
      {{ submitButtonText }}
    </button>
  </div>
</template>

<style scoped>
.configuration-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
}

.configuration-section {
  padding: 24px 22px;
  border-bottom: 1px solid var(--vf-border-light);
}

.configuration-section:nth-child(odd) {
  border-right: 1px solid var(--vf-border-light);
}

.configuration-label {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  margin-bottom: 15px;
}

.configuration-number {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 25px;
  height: 25px;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border-radius: 6px;
  font-size: 9px;
  font-weight: 700;
}

.configuration-label strong {
  display: block;
  color: var(--vf-text);
  font-size: 12px;
  font-weight: 700;
}

.configuration-label span:last-child {
  display: block;
  margin-top: 3px;
  color: var(--vf-light-muted);
  font-size: 10px;
}

.select-placeholder {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 54px;
  padding: 11px 13px;
  background: #fcfcfc;
  border: 1px solid var(--vf-border);
  border-radius: 7px;
}

.select-placeholder strong {
  display: block;
  color: var(--vf-muted);
  font-size: 11px;
  font-weight: 600;
}

.select-placeholder span:not(.select-arrow) {
  display: block;
  margin-top: 3px;
  color: var(--vf-light-muted);
  font-size: 9px;
}

.select-arrow {
  color: var(--vf-light-muted);
  font-size: 17px;
}

.task-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-option {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 54px;
  padding: 9px 11px;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 7px;
  cursor: pointer;
}

.task-option.selected {
  background: var(--vf-orange-soft);
  border-color: #fdba74;
}

.task-option-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--vf-orange-dark);
  background: #ffffff;
  border-radius: 7px;
  font-size: 9px;
  font-weight: 700;
}

.task-option strong {
  display: block;
  color: var(--vf-text);
  font-size: 11px;
  font-weight: 700;
}

.task-option span:not(.option-indicator) {
  display: block;
  margin-top: 3px;
  color: var(--vf-light-muted);
  font-size: 9px;
}

.option-indicator {
  width: 9px;
  height: 9px;
  margin-left: auto;
  border: 2px solid #d4d4d8;
  border-radius: 50%;
}

.task-option.selected .option-indicator {
  border-color: var(--vf-orange);
  background: var(--vf-orange);
  box-shadow: inset 0 0 0 2px #ffffff;
}

.feature-selection {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 7px;
}

.feature-check {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 7px 9px;
  color: var(--vf-text);
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
}

.feature-check.selected {
  background: var(--vf-orange-soft);
  border-color: #fed7aa;
}

.check-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: #ffffff;
  background: var(--vf-orange);
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
}

.algorithm-card {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 60px;
  padding: 10px 12px;
  background: var(--vf-orange-soft);
  border: 1px solid #fdba74;
  border-radius: 7px;
}

.algorithm-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  color: #ffffff;
  background: var(--vf-gradient);
  border-radius: 8px;
  font-size: 9px;
  font-weight: 700;
}

.algorithm-card strong {
  display: block;
  color: var(--vf-text);
  font-size: 11px;
}

.algorithm-card span {
  display: block;
  margin-top: 3px;
  color: var(--vf-light-muted);
  font-size: 9px;
}

.algorithm-status {
  margin-left: auto;
  padding: 4px 7px;
  color: var(--vf-orange-dark);
  background: #ffffff;
  border-radius: 4px;
  font-size: 8px !important;
  font-weight: 700;
}

.configuration-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 22px;
  background: #fcfcfc;
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

.configuration-footer strong {
  color: var(--vf-text);
  font-size: 11px;
  font-weight: 600;
}

.disabled-button {
  padding: 10px 15px;
  color: #a1a1aa;
  background: #f4f4f5;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: not-allowed;
}

@media (max-width: 800px) {
  .configuration-grid {
    grid-template-columns: 1fr;
  }
  .configuration-section:nth-child(odd) {
    border-right: none;
  }
}

@media (max-width: 700px) {
  .feature-selection {
    grid-template-columns: 1fr;
  }
  .configuration-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
