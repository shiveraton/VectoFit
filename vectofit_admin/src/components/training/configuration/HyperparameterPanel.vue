<script setup lang="ts">
import { computed } from "vue";

import HyperparameterCard from "./HyperparameterCard.vue";
import type { PredictionTarget } from "../../../services/trainingService";
import {
  FIXED_TRAINING_SETTINGS,
  TRAINING_PARAMETER_DEFINITIONS,
} from "./trainingParameters";

const props = defineProps<{
  hyperparameters: Record<string, unknown>;
  testSize: number;
  randomSeed: number;
  predictionTarget: PredictionTarget;
}>();

const emit = defineEmits<{
  (event: "set-hyperparameter", payload: { key: string; value: number }): void;
  (event: "set-test-size", value: number): void;
  (event: "set-random-seed", value: number): void;
}>();

const valueFor = (key: string, fallback: number) => {
  const raw = props.hyperparameters[key];
  return typeof raw === "number" ? raw : fallback;
};

const parameterValues = computed(() =>
  Object.fromEntries(
    TRAINING_PARAMETER_DEFINITIONS.map((definition) => [
      definition.key,
      definition.target === "hyperparameter"
        ? valueFor(definition.key, definition.defaultValue)
        : definition.target === "testSize"
          ? props.testSize
          : props.randomSeed,
    ]),
  ),
);

const baselineDescription = computed(
  () =>
    "Use the displayed baseline values as the reproducible starting configuration. Change them when the experiment requires a deliberate comparison.",
);

const effectiveFixedSettings = computed(() => {
  if (props.predictionTarget === "error_type") {
    return [
      { label: "Objective", value: "multi:softprob" },
      { label: "Evaluation Metric", value: "mlogloss" },
      { label: "Split Strategy", value: "group_by_participant" },
      { label: "Class Count", value: "Inferred from labels" },
    ];
  }

  return FIXED_TRAINING_SETTINGS;
});

const emitUpdate = (definitionKey: string, value: number) => {
  const definition = TRAINING_PARAMETER_DEFINITIONS.find(
    (item) => item.key === definitionKey,
  );
  if (!definition) return;

  if (definition.target === "hyperparameter") {
    emit("set-hyperparameter", { key: definition.key, value });
  } else if (definition.target === "testSize") {
    emit("set-test-size", value);
  } else {
    emit("set-random-seed", value);
  }
};
</script>

<template>
  <section class="configuration-section wide-section">
    <div class="configuration-label">
      <div>
        <strong>Training Parameters</strong>
        <span
          >Configure the XGBoost baseline and reproducible experiment
          settings.</span
        >
      </div>
    </div>

    <div class="parameter-intro">
      <div>
        <strong>How to use these controls</strong>
        <p>{{ baselineDescription }}</p>
      </div>
      <span class="parameter-count">
        {{ TRAINING_PARAMETER_DEFINITIONS.length }} settings
      </span>
    </div>

    <div class="parameter-grid">
      <HyperparameterCard
        v-for="definition in TRAINING_PARAMETER_DEFINITIONS"
        :key="definition.key"
        :definition="definition"
        :model-value="Number(parameterValues[definition.key])"
        @update="emitUpdate(definition.key, $event)"
      />
    </div>

    <div class="fixed-parameters">
      <span v-for="setting in effectiveFixedSettings" :key="setting.label">
        <strong>{{ setting.label }}</strong>
        <code>{{ setting.value }}</code>
      </span>
    </div>
  </section>
</template>

<style scoped>
.configuration-section {
  grid-column: 1 / -1;
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

.parameter-intro {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  margin-bottom: 13px;
  padding: 11px 12px;
  background: #fcfcfc;
  border: 1px solid var(--vf-border-light);
  border-radius: 8px;
}

.parameter-intro strong {
  color: var(--vf-text);
  font-size: 10px;
}

.parameter-intro p {
  margin: 4px 0 0;
  color: var(--vf-light-muted);
  font-size: 9px;
  line-height: 1.5;
}

.parameter-count {
  flex-shrink: 0;
  padding: 5px 8px;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 999px;
  font-size: 8px;
  font-weight: 800;
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.fixed-parameters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.fixed-parameters span {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  padding: 8px 10px;
  color: var(--vf-light-muted);
  background: #fafafa;
  border: 1px solid var(--vf-border-light);
  border-radius: 7px;
  font-size: 8px;
}

.fixed-parameters strong {
  color: var(--vf-muted);
}

.fixed-parameters code {
  overflow: hidden;
  color: var(--vf-text);
  font-family: Consolas, "Courier New", monospace;
  font-size: 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1050px) {
  .parameter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .fixed-parameters {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .parameter-grid {
    grid-template-columns: 1fr;
  }

  .parameter-intro {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>