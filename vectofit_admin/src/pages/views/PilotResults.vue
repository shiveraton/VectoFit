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
  <div class="pilot-page">
    <header class="page-header">
      <div>
        <div class="eyebrow">VECTOFIT EXPLORATORY PILOT</div>
        <h1>M0 / M1 Results</h1>
        <p>LOPO comparison of four-feature XGBoost M0 and six-feature XGBoost M1. The threshold rule is reported separately.</p>
      </div>
      <button class="secondary-button" type="button" :disabled="isLoading" @click="loadResults">
        {{ isLoading ? "Loading…" : "Refresh" }}
      </button>
    </header>

    <section v-if="error" class="panel message" role="alert">{{ error }}</section>
    <section v-else-if="isLoading" class="panel">Loading pilot results…</section>
    <template v-else-if="results">
      <section class="panel metadata">
        <strong>{{ results.label }}</strong>
        <span>Feature schema: {{ results.feature_schema_version }}</span>
        <span>Participants: {{ results.M0.per_participant.length }}</span>
        <span>Samples: {{ results.M0.oof_predictions?.length ?? "n/a" }}</span>
        <span>Exploratory pilot; LOPO estimates are not a validated clinical model.</span>
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
  </div>
</template>

<style scoped>


h1 { margin: 8px 0; }

h2 { margin-top: 0; font-size: 1rem; }

p { color: var(--vf-muted); }

.panel { margin-bottom: 18px; padding: 20px; background: #fff; border: 1px solid var(--vf-border); border-radius: 10px; overflow-x: auto; }

.metadata { display: flex; flex-wrap: wrap; gap: 20px; }

.message { color: #b42318; }





table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem; }

th, td { padding: 10px; border-bottom: 1px solid var(--vf-border); vertical-align: top; }

th { color: var(--vf-muted); font-size: 0.72rem; text-transform: uppercase; }

</style>
