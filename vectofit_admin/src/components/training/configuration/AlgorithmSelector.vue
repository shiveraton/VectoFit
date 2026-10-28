<script setup lang="ts">
import type { AlgorithmOption } from "../../../services/trainingService";

const props = defineProps<{
  algorithms: AlgorithmOption[];
  selectedAlgorithm: AlgorithmOption | null;
}>();

const emit = defineEmits<{
  (event: "select-algorithm", id: string): void;
}>();
</script>

<template>
  <section class="configuration-section">
    <div class="configuration-label">
      <div>
        <strong>Algorithm</strong>
        <span>Select the model family used for this run.</span>
      </div>
    </div>

    <div v-if="props.algorithms.length" class="algorithm-options">
      <button
        v-for="algorithm in props.algorithms"
        :key="algorithm.id"
        type="button"
        :class="[
          'algorithm-card',
          { selected: props.selectedAlgorithm?.id === algorithm.id },
        ]"
        @click="emit('select-algorithm', algorithm.id)"
      >
        <span class="algorithm-icon">{{ algorithm.code }}</span>
        <span class="algorithm-copy">
          <strong>{{ algorithm.name }}</strong>
          <span>{{ algorithm.description }}</span>
        </span>
        <span class="algorithm-status">
          {{
            props.selectedAlgorithm?.id === algorithm.id ? "Selected" : "Select"
          }}
        </span>
      </button>
    </div>

    <div v-else class="inline-empty">
      No supported training algorithms are currently available.
    </div>

    <div v-if="props.selectedAlgorithm" class="algorithm-note">
      VectoFit currently uses the configured XGBoost training pipeline for
      binary classification.
    </div>
  </section>
</template>

<style scoped>
.configuration-section {
  min-width: 0;
  padding: 24px 22px;
  border-bottom: 1px solid var(--vf-border-light);
}

.configuration-label {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  margin-bottom: 15px;
}

.configuration-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 27px;
  height: 27px;
  flex-shrink: 0;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 7px;
  font-size: 9px;
  font-weight: 800;
}

.configuration-label strong,
.configuration-label span {
  display: block;
}

.configuration-label strong {
  color: var(--vf-text);
  font-size: 12px;
}

.configuration-label div > span {
  margin-top: 4px;
  color: var(--vf-light-muted);
  font-size: 10px;
}

.algorithm-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.algorithm-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px;
  text-align: left;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.algorithm-card:hover {
  background: #fffaf6;
  border-color: #fdba74;
}

.algorithm-card.selected {
  background: var(--vf-orange-soft);
  border-color: #fb923c;
}

.algorithm-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  color: #ffffff;
  background: var(--vf-gradient);
  border-radius: 8px;
  font-size: 9px;
  font-weight: 800;
}

.algorithm-copy {
  min-width: 0;
  flex: 1;
}

.algorithm-copy strong,
.algorithm-copy span {
  display: block;
}

.algorithm-copy strong {
  color: var(--vf-text);
  font-size: 10px;
}

.algorithm-copy span {
  margin-top: 3px;
  color: var(--vf-light-muted);
  font-size: 9px;
  line-height: 1.45;
}

.algorithm-status {
  flex-shrink: 0;
  color: var(--vf-light-muted);
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
}

.selected .algorithm-status {
  color: var(--vf-orange-dark);
}

.algorithm-note,
.inline-empty {
  margin-top: 10px;
  color: var(--vf-light-muted);
  background: #fcfcfc;
  border: 1px dashed var(--vf-border);
  border-radius: 7px;
  font-size: 9px;
  line-height: 1.5;
}

.algorithm-note {
  padding: 9px 10px;
}

.inline-empty {
  padding: 15px;
  text-align: center;
}
</style>
