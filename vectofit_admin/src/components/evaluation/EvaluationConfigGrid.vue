<script setup lang="ts">
import type {
  EvaluationModel,
  EvaluationMetric,
} from "../../hooks/useEvaluation";

interface Props {
  selectedDataset: Record<string, any> | null;
  selectedModelId: string | null;
  models: EvaluationModel[];
  metrics: EvaluationMetric[];
  summaryText: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "select-model", modelId: string): void;
  (e: "toggle-metric", metricId: string): void;
  (e: "start-evaluation"): void;
}>();
</script>

<template>
  <div class="config-grid-container">
    <div class="config-sections">
      <div class="config-card">
        <div class="card-header">
          <span class="card-step">01</span>
          <div>
            <h3>Target Model Checkpoint</h3>
            <p>Select a trained model version to benchmark.</p>
          </div>
        </div>

        <div class="model-list">
          <div
            v-for="model in models"
            :key="model.id"
            class="model-option"
            :class="{ selected: model.id === selectedModelId }"
            @click="emit('select-model', model.id)"
          >
            <div class="model-radio">
              <span
                v-if="model.id === selectedModelId"
                class="radio-inner"
              ></span>
            </div>
            <div class="model-details">
              <div class="model-name-row">
                <span class="model-name">{{ model.name }}</span>
                <span class="model-version">v{{ model.version }}</span>
              </div>
              <div class="model-meta">
                <span class="model-type">{{ model.type }}</span>
                <span v-if="model.accuracy" class="model-accuracy">
                  Prev. Acc: {{ model.accuracy }}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="config-card">
        <div class="card-header">
          <span class="card-step">02</span>
          <div>
            <h3>Benchmark Metrics</h3>
            <p>Toggle biomechanical & vector metrics for scoring.</p>
          </div>
        </div>

        <div class="metrics-list">
          <div
            v-for="metric in metrics"
            :key="metric.id"
            class="metric-option"
            :class="{ active: metric.selected }"
            @click="emit('toggle-metric', metric.id)"
          >
            <div class="metric-checkbox">
              <span v-if="metric.selected" class="check-icon">✓</span>
            </div>
            <div class="metric-info">
              <div class="metric-header-row">
                <span class="metric-name">{{ metric.name }}</span>
                <span class="category-tag">{{ metric.category }}</span>
              </div>
              <p class="metric-description">{{ metric.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="config-footer">
      <div class="summary-info">
        <span class="summary-label">CONFIG SUMMARY</span>
        <p class="summary-text">{{ summaryText }}</p>
      </div>

      <button
        class="primary-button"
        :disabled="!selectedModelId || !selectedDataset"
        @click="emit('start-evaluation')"
      >
        <span class="button-icon">▶</span> Run Evaluation
      </button>
    </div>
  </div>
</template>

<style scoped>
.config-grid-container {
  padding: 24px;
}

.config-sections {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.config-card {
  background: var(--vf-surface, #1e293b);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.06));
}

.card-step {
  font-family: monospace;
  font-size: 11px;
  font-weight: 700;
  color: var(--vf-orange, #f97316);
  background: rgba(249, 115, 22, 0.12);
  padding: 3px 8px;
  border-radius: 6px;
}

.card-header h3 {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 700;
  color: var(--vf-dark, #f8fafc);
}

.card-header p {
  margin: 0;
  font-size: 11px;
  color: var(--vf-light-muted, #94a3b8);
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.model-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.06));
  cursor: pointer;
  transition: all 0.15s ease;
}

.model-option:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.12);
}

.model-option.selected {
  border-color: var(--vf-orange, #f97316);
  background: rgba(249, 115, 22, 0.06);
}

.model-radio {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--vf-muted, #64748b);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.model-option.selected .model-radio {
  border-color: var(--vf-orange, #f97316);
}

.radio-inner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--vf-orange, #f97316);
}

.model-details {
  flex: 1;
}

.model-name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.model-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--vf-dark, #f8fafc);
}

.model-version {
  font-size: 10px;
  font-weight: 700;
  color: var(--vf-orange, #f97316);
  background: rgba(249, 115, 22, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
}

.model-meta {
  display: flex;
  gap: 12px;
  margin-top: 4px;
  font-size: 11px;
  color: var(--vf-light-muted, #94a3b8);
}

.metrics-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.metric-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.06));
  cursor: pointer;
  transition: all 0.15s ease;
}

.metric-option:hover {
  background: rgba(255, 255, 255, 0.04);
}

.metric-option.active {
  border-color: rgba(74, 222, 128, 0.3);
  background: rgba(74, 222, 128, 0.04);
}

.metric-checkbox {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1.5px solid var(--vf-muted, #64748b);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
  flex-shrink: 0;
}

.metric-option.active .metric-checkbox {
  background: #4ade80;
  border-color: #4ade80;
}

.check-icon {
  color: #0f172a;
  font-size: 11px;
  font-weight: 900;
}

.metric-info {
  flex: 1;
}

.metric-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 3px;
}

.metric-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--vf-dark, #f8fafc);
}

.category-tag {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--vf-muted, #94a3b8);
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 6px;
  border-radius: 3px;
}

.metric-description {
  margin: 0;
  font-size: 11px;
  color: var(--vf-light-muted, #94a3b8);
  line-height: 1.4;
}

.config-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--vf-surface, #1e293b);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
}

.summary-label {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--vf-orange, #f97316);
}

.summary-text {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--vf-dark, #f8fafc);
  font-weight: 500;
}

.primary-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--vf-orange, #f97316);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.primary-button:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.primary-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.button-icon {
  font-size: 10px;
}

@media (max-width: 900px) {
  .config-sections {
    grid-template-columns: 1fr;
  }

  .config-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
  }

  .primary-button {
    width: 100%;
    justify-content: center;
  }
}
</style>
