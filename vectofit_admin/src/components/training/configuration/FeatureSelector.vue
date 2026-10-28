<script setup lang="ts">
import type { FeatureOption } from "../../../services/trainingService";

const props = defineProps<{
  features: FeatureOption[];
}>();

const emit = defineEmits<{
  (event: "toggle-feature", id: string): void;
}>();

const featureDescriptions: Record<string, string> = {
  rom: "Range of motion measurements.",
  asymmetry: "Left-right movement difference.",
  trunk: "Trunk inclination during the repetition.",
  knee: "Knee joint-angle measurement.",
  hip: "Hip joint-angle measurement.",
  velocity: "Kinematic movement velocity.",
};
</script>

<template>
  <section class="configuration-section">
    <div class="configuration-label">
      <div>
        <strong>Features</strong>
        <span>Measurements supplied to the classifier.</span>
      </div>
    </div>

    <div class="feature-selection">
      <button
        v-for="feature in props.features"
        :key="feature.id"
        type="button"
        :class="['feature-option', { selected: feature.selected }]"
        @click="emit('toggle-feature', feature.id)"
      >
        <span class="check-box" aria-hidden="true">
          {{ feature.selected ? "✓" : "" }}
        </span>
        <span class="feature-copy">
          <strong>{{ feature.name }}</strong>
          <small>{{
            featureDescriptions[feature.id] || "Selected model feature."
          }}</small>
        </span>
      </button>
    </div>

    <p class="feature-note">
      Selected measurements are passed to the configured classifier for this
      experiment.
    </p>
  </section>
</template>

<style scoped>
.configuration-section {
  min-width: 0;
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

.feature-selection {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.feature-option {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 10px;
  text-align: left;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.feature-option:hover {
  background: #fffaf6;
  border-color: #fdba74;
}

.feature-option.selected {
  background: var(--vf-orange-soft);
  border-color: #fed7aa;
}

.check-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 17px;
  height: 17px;
  flex-shrink: 0;
  color: #ffffff;
  background: #ffffff;
  border: 1.5px solid #d4d4d8;
  border-radius: 5px;
  font-size: 10px;
  font-weight: 800;
}

.selected .check-box {
  background: var(--vf-gradient);
  border-color: transparent;
}

.feature-copy {
  min-width: 0;
}

.feature-copy strong,
.feature-copy small {
  display: block;
}

.feature-copy strong {
  color: var(--vf-text);
  font-size: 10px;
  font-weight: 700;
}

.feature-copy small {
  margin-top: 3px;
  color: var(--vf-light-muted);
  font-size: 8px;
  line-height: 1.4;
}

.feature-note {
  margin: 11px 0 0;
  color: var(--vf-light-muted);
  font-size: 9px;
  line-height: 1.5;
}

@media (max-width: 900px) {
  .feature-selection {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 800px) {
  .configuration-section:nth-child(odd) {
    border-right: none;
  }
}
</style>
