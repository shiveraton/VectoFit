<script setup lang="ts">
import type { FeatureOption } from "../../../services/trainingService";

const props = defineProps<{
  features: FeatureOption[];
}>();

const featureDescriptions: Record<string, string> = {
  fppa_l_bottom: "Signed left knee angle at squat bottom.",
  fppa_r_bottom: "Signed right knee angle at squat bottom.",
  fppa_l_peak: "Largest absolute filtered left FPPA in the repetition.",
  fppa_r_peak: "Largest absolute filtered right FPPA in the repetition.",
  asym_bottom: "Absolute left-right FPPA difference at squat bottom.",
  asym_peak: "Absolute left-right difference between peak FPPA values.",
};
</script>

<template>
  <section class="configuration-section">
    <div class="configuration-label">
      <div>
        <strong>FPPA v2 Feature Schema</strong>
        <span>Six fixed inputs used by the current M1 model.</span>
      </div>
    </div>

    <div class="feature-selection">
      <div
        v-for="feature in props.features"
        :key="feature.id"
        :class="['feature-option', { selected: feature.selected }]"
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
      </div>
    </div>

    <p class="feature-note">
      The fixed schema keeps training inputs aligned with frontal-plane FPPA assessment and model provenance.
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
  font-size: 11px;
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
  font-size: 12px;
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
  cursor: default;
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
  font-size: 12px;
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
  font-size: 12px;
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
  font-size: 11px;
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
