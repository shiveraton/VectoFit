<script setup lang="ts">
import { onMounted, watch } from "vue";
import ExperimentReadiness from "../../components/experiments/ExperimentReadiness.vue";
import ExperimentResultsPanel from "../../components/experiments/ExperimentResultsPanel.vue";
import { useExperimentReadiness, useExperimentResults } from "../../hooks/useExperiment";

const {
  datasetIdsText,
  viewAngle,
  report,
  isLoading,
  error,
  fragileParticipants,
  load,
} = useExperimentReadiness();

const {
  bundle,
  response: resultsResponse,
  isLoading: resultsLoading,
  error: resultsError,
  load: loadResults,
} = useExperimentResults();

onMounted(() => {
  load();
  loadResults();
});
watch(bundle, loadResults);
</script>

<template>
  <main class="page">
    <header class="head">
      <div>
        <div class="eyebrow">VECTOFIT EXPERIMENTS</div>
        <h1>M0 vs M1, leave-one-participant-out</h1>
        <p>Does bilateral asymmetry add value over signed FPPA alone?</p>
      </div>
      <span class="pilot">Exploratory pilot</span>
    </header>

    <form class="controls" @submit.prevent="load">
      <label>
        Dataset IDs
        <input v-model="datasetIdsText" placeholder="17" />
      </label>
      <label>
        Camera angle
        <select v-model="viewAngle">
          <option value="frontal">Frontal</option>
          <option value="sagittal">Sagittal</option>
          <option value="diagonal">Diagonal</option>
        </select>
      </label>
      <button type="submit" :disabled="isLoading">
        {{ isLoading ? "Checking…" : "Check readiness" }}
      </button>
    </form>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <ExperimentReadiness v-if="report" :report="report" />

    <p v-if="fragileParticipants.length" class="warning">
      {{ fragileParticipants.join(", ") }}: a single repetition in one class.
      Held-out results for these participants hinge on that one rep.
    </p>

    <div class="controls">
      <label>
        Results bundle
        <select v-model="bundle">
          <option value="main">Frozen run</option>
          <option value="demo">Synthetic demo</option>
        </select>
      </label>
    </div>

    <p v-if="resultsError" class="error" role="alert">{{ resultsError }}</p>

    <ExperimentResultsPanel
      v-if="resultsResponse?.available"
      :data="resultsResponse"
    />
    <section v-else-if="!resultsLoading" class="placeholder">
      <h2>2. Results</h2>
      <p v-if="bundle === 'demo'">
        No demo bundle yet. Run
        <code>python manage.py run_experiment --demo --out ../research/experiments/demo</code>.
      </p>
      <p v-else>No frozen run yet. Nothing here is a result.</p>
    </section>
  </main>
</template>

<style scoped>
.page {
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  color: var(--vf-dark, #f8fafc);
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}
.head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--vf-orange, #f97316);
}
h1 {
  margin: 4px 0;
  font-size: 22px;
}
.head p {
  margin: 0;
  font-size: 13px;
  color: var(--vf-light-muted, #94a3b8);
}
.pilot {
  align-self: flex-start;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.12);
}
.controls {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.controls label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: var(--vf-light-muted, #94a3b8);
}
.controls input,
.controls select {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.12));
  background: var(--vf-surface, #1e293b);
  color: var(--vf-dark, #f8fafc);
}
.controls button {
  padding: 9px 16px;
  border-radius: 8px;
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.12));
  background: transparent;
  color: var(--vf-dark, #f8fafc);
  cursor: pointer;
}
.error {
  color: #f87171;
  font-size: 13px;
}
.warning {
  font-size: 12px;
  color: #fbbf24;
}
.placeholder {
  border: 1px dashed var(--vf-border-light, rgba(255, 255, 255, 0.15));
  border-radius: 12px;
  padding: 20px;
}
.placeholder h2 {
  margin: 0 0 6px;
  font-size: 14px;
}
.placeholder p {
  margin: 0;
  font-size: 12px;
  color: var(--vf-light-muted, #94a3b8);
}
</style>
