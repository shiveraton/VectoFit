<script setup lang="ts">
const props = defineProps<{
  values: Array<{ name: string; value: number }>;
}>();

const maximum = () => Math.max(...props.values.map((item) => item.value), 0.000001);
</script>

<template>
  <section class="result-panel">
    <header class="result-panel-header">
      <div>
        <h3>What influenced the model?</h3>
        <p>Relative feature importance reported by the trained XGBoost model.</p>
      </div>
      <span v-if="values.length" class="top-feature">
        Top: <strong>{{ values[0].name }}</strong>
      </span>
    </header>

    <div v-if="values.length" class="importance-list">
      <div v-for="feature in values" :key="feature.name" class="importance-row">
        <div class="importance-label">
          <span>{{ feature.name }}</span>
          <strong>{{ (feature.value * 100).toFixed(1) }}%</strong>
        </div>
        <div class="importance-track">
          <div
            class="importance-fill"
            :style="{ width: `${(feature.value / maximum()) * 100}%` }"
          ></div>
        </div>
      </div>
    </div>

    <div v-else class="panel-empty">No feature importance data is available for this run.</div>

    <div class="interpretation-box">
      <span>How to interpret this</span>
      <p>
        Larger values indicate a greater contribution to the trained model's decision process. They do not mean the feature independently causes correct or incorrect squat form.
      </p>
    </div>
  </section>
</template>

<style scoped>
.result-panel {
  min-width: 0;
  padding: 18px;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 10px;
}

.result-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 15px;
}

.result-panel-header h3 {
  margin: 0;
  color: var(--vf-text);
  font-size: 12px;
}

.result-panel-header p {
  margin: 4px 0 0;
  color: var(--vf-light-muted);
  font-size: 11px;
  line-height: 1.5;
}

.top-feature {
  flex-shrink: 0;
  padding: 5px 8px;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 999px;
  font-size: 12px;
}

.top-feature strong {
  color: var(--vf-text);
}

.importance-list {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.importance-label {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
  color: var(--vf-muted);
  font-size: 11px;
}

.importance-label strong {
  color: var(--vf-text);
}

.importance-track {
  height: 7px;
  overflow: hidden;
  background: #f4f4f5;
  border-radius: 999px;
}

.importance-fill {
  height: 100%;
  min-width: 2px;
  background: var(--vf-gradient);
  border-radius: inherit;
  transition: width 0.25s ease;
}

.panel-empty {
  margin-top: 16px;
  padding: 18px;
  color: var(--vf-light-muted);
  background: #fafafa;
  border: 1px dashed var(--vf-border);
  border-radius: 8px;
  text-align: center;
  font-size: 11px;
}

.interpretation-box {
  margin-top: 16px;
  padding: 11px;
  background: #fffaf6;
  border: 1px solid #fed7aa;
  border-radius: 8px;
}

.interpretation-box span {
  color: var(--vf-orange-dark);
  font-size: 11px;
  font-weight: 800;
}

.interpretation-box p {
  margin: 5px 0 0;
  color: var(--vf-muted);
  font-size: 11px;
  line-height: 1.55;
}
</style>
