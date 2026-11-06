<script setup lang="ts">
import { computed } from "vue";
import type { ModelState } from "../../services/modelService";

const props = defineProps<{
  features: ModelState["features"];
}>();

const featureLabels: Record<string, string> = {
  fppa_l_bottom: "Left FPPA at squat bottom",
  fppa_r_bottom: "Right FPPA at squat bottom",
  fppa_l_peak: "Left peak FPPA",
  fppa_r_peak: "Right peak FPPA",
  asym_bottom: "Bottom bilateral asymmetry",
  asym_peak: "Peak bilateral asymmetry",
};

const groups = computed(() => {
  const selected = new Set(props.features.selected);
  const fppaFeatures = [
    "fppa_l_bottom",
    "fppa_r_bottom",
    "fppa_l_peak",
    "fppa_r_peak",
    "asym_bottom",
    "asym_peak",
  ];

  return [
    {
      title: "FPPA v2 · M1 Input Features",
      features: fppaFeatures.filter((key) => selected.has(key)),
    },
  ].filter((group) => group.features.length > 0);
});

const importanceRows = computed(() =>
  Object.entries(props.features.importances)
    .map(([name, value]) => ({
      name,
      label: featureLabels[name] ?? name,
      value: Number(value),
    }))
    .filter((row) => Number.isFinite(row.value))
    .sort((a, b) => b.value - a.value),
);

const maxImportance = computed(() =>
  importanceRows.value.reduce((max, row) => Math.max(max, row.value), 0),
);

const labelFor = (name: string) => featureLabels[name] ?? name;
</script>

<template>
  <div class="feature-layout">
    <div class="feature-set">
      <div v-for="group in groups" :key="group.title" class="feature-group">
        <div class="group-title">
          {{ group.title }}
        </div>

        <div class="feature-list">
          <span
            v-for="feature in group.features"
            :key="feature"
            class="feature-chip"
          >
            {{ labelFor(feature) }}
          </span>
        </div>
      </div>
    </div>

    <div class="importance-panel">
      <div class="subheading">Feature importance</div>

      <p class="helper">
        Relative contribution reported by the trained XGBoost M1 model.
      </p>

      <div v-if="importanceRows.length" class="importance-list">
        <div
          v-for="row in importanceRows"
          :key="row.name"
          class="importance-row"
        >
          <div class="importance-meta">
            <span>{{ row.label }}</span>
            <span> {{ (row.value * 100).toFixed(1) }}% </span>
          </div>

          <div class="importance-track">
            <div
              class="importance-fill"
              :style="{
                width: `${
                  maxImportance ? (row.value / maxImportance) * 100 : 0
                }%`,
              }"
            ></div>
          </div>
        </div>
      </div>

      <div v-else class="empty-detail">
        Feature importance is not available for this model.
      </div>
    </div>
  </div>
</template>

<style scoped>
.feature-layout {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: 24px;
  padding: 24px;
}

.feature-group + .feature-group {
  margin-top: 18px;
}

.group-title {
  margin-bottom: 8px;
  color: var(--vf-muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.feature-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feature-chip {
  padding: 8px 10px;
  border: 1px solid var(--vf-border-light);
  border-radius: 8px;
  background: #fafafa;
  color: var(--vf-dark);
  font-size: 13px;
}

.importance-panel {
  border-left: 1px solid var(--vf-border-light);
  padding-left: 24px;
}

.subheading {
  color: var(--vf-dark);
  font-size: 13px;
  font-weight: 700;
}

.helper {
  margin: 5px 0 18px;
  color: var(--vf-muted);
  font-size: 13px;
  line-height: 1.5;
}

.importance-row + .importance-row {
  margin-top: 13px;
}

.importance-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 5px;
  color: var(--vf-dark);
  font-size: 13px;
}

.importance-meta span:last-child {
  color: var(--vf-muted);
  font-variant-numeric: tabular-nums;
}

.importance-track {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: #f0f0f0;
}

.importance-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--vf-gradient);
}

.empty-detail {
  padding: 18px 0;
  color: var(--vf-muted);
  font-size: 13px;
}

@media (max-width: 820px) {
  .feature-layout {
    grid-template-columns: 1fr;
  }

  .importance-panel {
    border-left: 0;
    border-top: 1px solid var(--vf-border-light);
    padding: 20px 0 0;
  }
}
</style>
