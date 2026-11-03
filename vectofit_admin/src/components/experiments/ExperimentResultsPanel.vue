<script setup lang="ts">
import { computed } from "vue";
import type { ExperimentResultsResponse } from "../../services/experimentService";
import DeltaStrip from "./DeltaStrip.vue";

const props = defineProps<{ data: ExperimentResultsResponse }>();

const r = computed(() => props.data.results!);
const main = computed(() => r.value.main);
const delta = computed(() => main.value.delta_macro_f1_M1_minus_M0);
const boot = computed(() => delta.value.bootstrap);
const jack = computed(() => delta.value.jackknife);
const code = (group: string) => props.data.participant_codes?.[group] ?? group;

const f = (v: number) => v.toFixed(3);
const signed = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(3)}`;

const entries = computed(() =>
  Object.entries(jack.value.without_participant).map(([g, value]) => ({
    label: code(g),
    value,
    flips: jack.value.sign_flips.includes(g),
  })),
);

const RULE_LABELS: Record<string, string> = {
  abs_peak: "Rule · peak FPPA, tuned in-fold",
  abs_bottom: "Rule · bottom FPPA, tuned in-fold",
};
const tableRows = computed(() => [
  { name: "M0 · signed FPPA", m: main.value.models.M0 },
  { name: "M1 · plus asymmetry", m: main.value.models.M1 },
  ...Object.entries(main.value.rule_baseline).map(([k, v]) => ({
    name: RULE_LABELS[k] ?? k,
    m: v.metrics,
  })),
]);

const sensitivity = computed(() =>
  Object.entries(r.value.sensitivity).map(([key, block]) => ({
    who: code(key.replace(/^exclude_/, "")),
    delta: block.delta_macro_f1_M1_minus_M0.bootstrap.point_delta,
    m0: block.models.M0.macro_f1,
    m1: block.models.M1.macro_f1,
  })),
);
</script>

<template>
  <section class="card">
    <header class="card-head">
      <h2>2. Results</h2>
      <span class="muted">
        {{ r.n_participants }} participants · {{ r.n_reps }} reps · seed
        {{ r.seed }}
      </span>
    </header>

    <div v-if="r.demo" class="notice danger">
      Synthetic demo data. These numbers are not results.
    </div>
    <p class="semantics"><span>Label semantics</span>{{ r.label_semantics }}</p>

    <div class="cards">
      <div class="stat">
        <span class="lbl">M0 · signed FPPA</span>
        <strong>{{ f(main.models.M0.macro_f1) }}</strong>
        <span class="lbl">macro-F1</span>
      </div>
      <div class="stat">
        <span class="lbl">M1 · plus asymmetry</span>
        <strong>{{ f(main.models.M1.macro_f1) }}</strong>
        <span class="lbl">macro-F1</span>
      </div>
      <div class="stat accent">
        <span class="lbl">Δ macro-F1, M1 − M0</span>
        <strong>{{ signed(boot.point_delta) }}</strong>
        <span class="lbl">
          [{{ signed(boot.delta_ci[0]) }}, {{ signed(boot.delta_ci[1]) }}] ·
          {{ boot.n_participants }} clusters, descriptive only
        </span>
      </div>
      <div class="stat" :class="{ warn: jack.sign_flips.length }">
        <span class="lbl">Sign flips on removal</span>
        <strong>{{
          jack.sign_flips.length ? jack.sign_flips.map(code).join(", ") : "None"
        }}</strong>
        <span class="lbl"
          >range {{ signed(jack.min) }} to {{ signed(jack.max) }}</span
        >
      </div>
    </div>

    <h3>Does Δ survive removing one participant?</h3>
    <DeltaStrip
      :full="jack.full_delta"
      :ci="boot.delta_ci"
      :entries="entries"
    />

    <h3>Models and baselines</h3>
    <table>
      <thead>
        <tr>
          <th>Model</th>
          <th>macro-F1</th>
          <th>Bad F1</th>
          <th>Bad recall</th>
          <th>Bal. acc.</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in tableRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ f(row.m.macro_f1) }}</td>
          <td>{{ f(row.m.bad.f1) }}</td>
          <td>{{ f(row.m.bad.recall) }}</td>
          <td>{{ f(row.m.balanced_accuracy) }}</td>
        </tr>
      </tbody>
    </table>

    <h3>Per participant</h3>
    <table>
      <thead>
        <tr>
          <th>Who</th>
          <th>Reps</th>
          <th>Bad</th>
          <th>M0 correct</th>
          <th>M1 correct</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in delta.per_participant" :key="p.participant">
          <td>{{ code(p.participant) }}</td>
          <td>{{ p.n_reps }}</td>
          <td :class="{ bad: p.n_bad === 1 }">{{ p.n_bad }}</td>
          <td>{{ p.a_correct }}</td>
          <td>{{ p.b_correct }}</td>
        </tr>
      </tbody>
    </table>

    <template v-if="sensitivity.length">
      <h3>Full rerun excluding one participant</h3>
      <p v-for="s in sensitivity" :key="s.who" class="line">
        Without {{ s.who }}: Δ {{ signed(s.delta) }} (M0 {{ f(s.m0) }}, M1
        {{ f(s.m1) }})
      </p>
    </template>

    <h3>Limits</h3>
    <ul class="limits">
      <li>Exploratory pilot evidence only; not evidence of generalization.</li>
      <li>
        Labels are not verified knee-alignment ground truth; see label semantics
        above.
      </li>
      <li>
        The asymmetry features are |L − R| of M0's own features: engineered
        structure, not new measurements.
      </li>
      <li>Pre-declared decision rule: {{ r.decision_rule }}</li>
    </ul>
  </section>
</template>

<style scoped>
.card {
  background: var(--vf-surface, #1e293b);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  padding: 20px;
  color: var(--vf-dark, #f8fafc);
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.card-head h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}
h3 {
  margin: 22px 0 8px;
  font-size: 13px;
  font-weight: 700;
}
.muted,
.lbl {
  font-size: 11px;
  color: var(--vf-light-muted, #94a3b8);
}
.semantics {
  font-size: 12px;
  color: var(--vf-light-muted, #94a3b8);
  margin: 4px 0 14px;
}
.semantics span {
  margin-right: 8px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.notice.danger {
  margin: 8px 0;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
  color: #f87171;
  background: rgba(239, 68, 68, 0.1);
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}
.stat strong {
  font-size: 22px;
}
.stat.accent {
  background: rgba(249, 115, 22, 0.1);
}
.stat.warn {
  background: rgba(239, 68, 68, 0.1);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th {
  text-align: left;
  padding: 8px;
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--vf-muted, #94a3b8);
  border-bottom: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
}
td {
  padding: 8px;
  border-bottom: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.05));
}
td.bad {
  color: #f87171;
}
.line {
  margin: 4px 0;
  font-size: 13px;
}
.limits {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--vf-light-muted, #94a3b8);
  line-height: 1.7;
}
</style>
