<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  pilotResultsService,
  type PilotMetricResult,
  type PilotResults,
} from "../../services/pilotResultsService";

const results = ref<PilotResults | null>(null);
const error = ref<string | null>(null);
const isLoading = ref(true);

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
const formatInterval = (value: number) => `${value.toFixed(3)}`;

const loadResults = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    results.value = await pilotResultsService.getResults();
  } catch {
    error.value = "No pilot results are available. Run run_m0_m1 first.";
  } finally {
    isLoading.value = false;
  }
};

const participantRows = (result: PilotMetricResult) => result.per_participant;

onMounted(loadResults);
</script>

<template>
  <main class="pilot-page">
    <header class="page-header">
      <div>
        <div class="eyebrow">VECTOFIT EXPLORATORY PILOT</div>
        <h1>M0 / M1 Results</h1>
        <p>Read-only results from the fixed LOPO evaluation and baseline.</p>
      </div>
      <button class="refresh-button" type="button" :disabled="isLoading" @click="loadResults">
        {{ isLoading ? "Loading…" : "Refresh" }}
      </button>
    </header>

    <section v-if="error" class="panel message" role="alert">{{ error }}</section>
    <section v-else-if="isLoading" class="panel">Loading pilot results…</section>
    <template v-else-if="results">
      <section class="panel metadata">
        <strong>{{ results.label }}</strong>
        <span>Feature schema: {{ results.feature_schema_version }}</span>
        <span>Delta M1 − M0: {{ formatPercent(results.delta_macro_f1) }}</span>
        <span>
          Bootstrap 95% interval:
          [{{ formatInterval(results.delta_macro_f1_bootstrap_95.lower) }},
          {{ formatInterval(results.delta_macro_f1_bootstrap_95.upper) }}]
        </span>
      </section>

      <section class="panel">
        <h2>LOPO model comparison</h2>
        <table>
          <thead><tr><th>Model</th><th>Features</th><th>Macro-F1</th><th>Participants</th></tr></thead>
          <tbody>
            <tr><td>M0</td><td>{{ results.M0_features.join(", ") }}</td><td>{{ formatPercent(results.M0.macro_f1) }}</td><td>{{ results.M0.per_participant.length }}</td></tr>
            <tr><td>M1</td><td>{{ results.M1_features.join(", ") }}</td><td>{{ formatPercent(results.M1.macro_f1) }}</td><td>{{ results.M1.per_participant.length }}</td></tr>
          </tbody>
        </table>
      </section>

      <section class="panel">
        <h2>Fixed threshold baseline</h2>
        <p>{{ results.threshold_rule_baseline.rule }}</p>
        <table>
          <thead><tr><th>Run</th><th>Cutoff</th><th>Macro-F1</th><th>Confusion matrix</th></tr></thead>
          <tbody>
            <tr>
              <td>{{ results.threshold_rule_baseline.primary.label }}</td>
              <td>{{ results.threshold_rule_baseline.primary.cutoff_degrees.valgus }}° / {{ results.threshold_rule_baseline.primary.cutoff_degrees.varus }}°</td>
              <td>{{ formatPercent(results.threshold_rule_baseline.primary.macro_f1) }}</td>
              <td>{{ results.threshold_rule_baseline.primary.confusion_matrix.join(" / ") }}</td>
            </tr>
            <tr v-for="run in results.threshold_rule_baseline.sensitivity" :key="run.cutoff_degrees.valgus">
              <td>{{ run.label }}</td>
              <td>{{ run.cutoff_degrees.valgus }}° / {{ run.cutoff_degrees.varus }}°</td>
              <td>{{ formatPercent(run.macro_f1) }}</td>
              <td>{{ run.confusion_matrix.join(" / ") }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="panel">
        <h2>Per-participant LOPO macro-F1</h2>
        <table>
          <thead><tr><th>Participant</th><th>M0</th><th>M1</th><th>Samples</th></tr></thead>
          <tbody>
            <tr v-for="row in participantRows(results.M0)" :key="row.participant">
              <td>{{ row.participant }}</td>
              <td>{{ formatPercent(row.macro_f1) }}</td>
              <td>{{ formatPercent(results.M1.per_participant.find((item) => item.participant === row.participant)?.macro_f1 ?? 0) }}</td>
              <td>{{ row.sample_count }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </main>
</template>

<style scoped>
.pilot-page { max-width: 1200px; margin: 0 auto; color: #25201e; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.eyebrow { color: #e94b23; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; }
h1 { margin: 8px 0; }
h2 { margin-top: 0; font-size: 1rem; }
p { color: #766d69; }
.panel { margin-bottom: 18px; padding: 20px; background: #fff; border: 1px solid #eee6e2; border-radius: 10px; overflow-x: auto; }
.metadata { display: flex; flex-wrap: wrap; gap: 20px; }
.message { color: #b42318; }
button { padding: 9px 14px; border: 1px solid #e94b23; border-radius: 7px; background: #fff; color: #e94b23; cursor: pointer; }
button:disabled { opacity: 0.6; cursor: wait; }
table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem; }
th, td { padding: 10px; border-bottom: 1px solid #eee6e2; vertical-align: top; }
th { color: #766d69; font-size: 0.72rem; text-transform: uppercase; }
</style>
