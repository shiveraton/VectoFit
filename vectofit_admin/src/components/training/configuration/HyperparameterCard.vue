<script setup lang="ts">
import { computed, ref } from "vue";

import ParameterSimulation from "./ParameterSimulation.vue";
import type { TrainingParameterDefinition } from "./trainingParameters";

const props = defineProps<{
  definition: TrainingParameterDefinition;
  modelValue: number;
}>();

const emit = defineEmits<{
  (event: "update", value: number): void;
}>();

const showHelp = ref(false);

const progress = computed(() => {
  const range = props.definition.max - props.definition.min;
  if (!range) return 0;
  return ((props.modelValue - props.definition.min) / range) * 100;
});

const displayValue = computed(() => {
  const value = props.modelValue;

  if (props.definition.format === "percent") {
    return `${Math.round(value * 100)}%`;
  }

  if (props.definition.format === "decimal") {
    return value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  }

  return Math.round(value).toLocaleString("en-US");
});

const updateValue = (rawValue: string | number) => {
  const numericValue = Number(rawValue);
  if (!Number.isFinite(numericValue)) return;

  const clamped = Math.min(
    props.definition.max,
    Math.max(props.definition.min, numericValue),
  );

  emit("update", clamped);
};
</script>

<template>
  <article class="parameter-card">
    <header class="parameter-header">
      <div class="parameter-heading">
        <span class="parameter-title">{{ definition.title }}</span>
        <span class="technical-name">{{ definition.technicalName }}</span>
      </div>

      <button
        type="button"
        class="help-button"
        :aria-expanded="showHelp"
        :aria-label="`Explain ${definition.title}`"
        @click="showHelp = !showHelp"
      >
        ?
      </button>
    </header>

    <div class="parameter-question">
      {{ definition.question }}
    </div>

    <div class="parameter-control">
      <input
        v-if="definition.inputType === 'range'"
        class="parameter-range"
        type="range"
        :min="definition.min"
        :max="definition.max"
        :step="definition.step"
        :value="modelValue"
        :style="{ '--parameter-progress': `${Math.min(100, Math.max(0, progress))}%` }"
        :aria-label="definition.title"
        @input="updateValue(($event.target as HTMLInputElement).value)"
      />

      <input
        v-else
        class="parameter-number"
        type="number"
        :min="definition.min"
        :max="definition.max"
        :step="definition.step"
        :value="modelValue"
        :aria-label="definition.title"
        @input="updateValue(($event.target as HTMLInputElement).value)"
      />

      <output class="parameter-value">{{ displayValue }}</output>
    </div>

    <div class="parameter-scale">
      <span>{{ definition.lowLabel }}</span>
      <span>{{ definition.highLabel }}</span>
    </div>

    <ParameterSimulation
      :variant="definition.simulation"
      :progress="progress"
    />

    <div class="parameter-recommendation">
      <span>Baseline</span>
      <strong>{{ definition.recommended }}</strong>
    </div>

    <Transition name="help-fade">
      <div v-if="showHelp" class="parameter-help">
        <p>{{ definition.description }}</p>
        <div class="help-effects">
          <span><strong>Lower:</strong> {{ definition.lowEffect }}</span>
          <span><strong>Higher:</strong> {{ definition.highEffect }}</span>
        </div>
      </div>
    </Transition>
  </article>
</template>

<style scoped>
.parameter-card {
  position: relative;
  min-width: 0;
  padding: 15px;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(24, 24, 27, 0.02);
}

.parameter-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.parameter-heading {
  min-width: 0;
}

.parameter-title,
.technical-name {
  display: block;
}

.parameter-title {
  color: var(--vf-text);
  font-size: 11px;
  font-weight: 700;
}

.technical-name {
  margin-top: 2px;
  color: var(--vf-light-muted);
  font-family: Consolas, "Courier New", monospace;
  font-size: 8px;
}

.help-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 19px;
  height: 19px;
  flex-shrink: 0;
  color: var(--vf-muted);
  background: #fafafa;
  border: 1px solid var(--vf-border);
  border-radius: 50%;
  cursor: pointer;
  font-size: 9px;
  font-weight: 800;
  transition: all 0.15s ease;
}

.help-button:hover,
.help-button[aria-expanded="true"] {
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border-color: #fed7aa;
}

.parameter-question {
  margin-top: 10px;
  color: var(--vf-muted);
  font-size: 9px;
  line-height: 1.55;
}

.parameter-control {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 13px;
}

.parameter-range {
  width: 100%;
  accent-color: var(--vf-orange);
  cursor: pointer;
}

.parameter-range::-webkit-slider-runnable-track {
  height: 5px;
  background: linear-gradient(
    to right,
    #fb923c var(--parameter-progress),
    #e4e4e7 var(--parameter-progress)
  );
  border-radius: 999px;
}

.parameter-range::-moz-range-track {
  height: 5px;
  background: #e4e4e7;
  border-radius: 999px;
}

.parameter-range::-moz-range-progress {
  height: 5px;
  background: #fb923c;
  border-radius: 999px;
}

.parameter-number {
  width: 100%;
  min-width: 0;
  padding: 8px 9px;
  color: var(--vf-text);
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 7px;
  outline: none;
  font-family: inherit;
  font-size: 10px;
  font-weight: 700;
}

.parameter-number:focus {
  border-color: #fb923c;
  box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.08);
}

.parameter-value {
  min-width: 54px;
  padding: 7px 8px;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 7px;
  text-align: center;
  font-size: 10px;
  font-weight: 800;
}

.parameter-scale {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 6px;
  color: var(--vf-light-muted);
  font-size: 8px;
}

.parameter-recommendation {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 9px;
  color: var(--vf-light-muted);
  font-size: 8px;
}

.parameter-recommendation strong {
  color: var(--vf-muted);
  font-size: 9px;
}

.parameter-help {
  margin-top: 10px;
  padding: 10px;
  color: var(--vf-muted);
  background: #fffaf6;
  border: 1px solid #fed7aa;
  border-radius: 7px;
  font-size: 9px;
  line-height: 1.5;
}

.parameter-help p {
  margin: 0;
}

.help-effects {
  display: grid;
  gap: 4px;
  margin-top: 7px;
}

.help-effects strong {
  color: var(--vf-text);
}

.help-fade-enter-active,
.help-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.help-fade-enter-from,
.help-fade-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}
</style>
