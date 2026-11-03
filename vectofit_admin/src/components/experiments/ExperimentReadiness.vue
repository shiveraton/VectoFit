<script setup lang="ts">
import { computed } from "vue";
import type { ReadinessReport } from "../../services/experimentService";

const props = defineProps<{ report: ReadinessReport }>();

const maxReps = computed(() =>
  Math.max(1, ...props.report.participants.map((p) => p.good + p.bad)),
);
const pct = (n: number) => `${(n / maxReps.value) * 100}%`;
const isFragile = (good: number, bad: number) => good === 1 || bad === 1;
const provenance = (total: number, human: number) =>
  human === 0 ? "Folder labels only" : `${human} of ${total} human-annotated`;
</script>

<template>
  <section class="card">
    <header class="card-head">
      <h2>1. Readiness</h2>
      <span class="muted"
        >{{ report.n_reps }} reps · {{ report.view_angle }}</span
      >
    </header>

    <div v-if="report.reason" class="notice danger">{{ report.reason }}</div>

    <div class="row head">
      <span>Who</span><span>Good / Bad reps</span><span>Counts</span
      ><span>Label provenance</span>
    </div>

    <div
      v-for="p in report.participants"
      :key="p.group"
      class="row"
      :class="{ fragile: isFragile(p.good, p.bad) }"
    >
      <strong>{{ p.code }}</strong>
      <div class="bar">
        <div class="seg good" :style="{ width: pct(p.good) }"></div>
        <div class="seg bad" :style="{ width: pct(p.bad) }"></div>
      </div>
      <span>{{ p.good }} / {{ p.bad }}</span>
      <span>
        <span v-if="isFragile(p.good, p.bad)" class="chip danger">
          Single {{ p.bad === 1 ? "Bad" : "Good" }} rep
        </span>
        <span v-else class="chip" :class="{ warn: p.human_labelled === 0 }">
          {{ provenance(p.good + p.bad, p.human_labelled) }}
        </span>
      </span>
    </div>

    <footer class="chips">
      <span class="chip" :class="report.lopo.viable ? 'ok' : 'danger'">
        {{
          report.lopo.viable
            ? `${report.lopo.folds} LOPO folds`
            : `LOPO not viable: ${report.lopo.reason}`
        }}
      </span>
      <span class="chip" :class="{ danger: report.mixed_pipeline }">
        {{ report.pipeline_hash_count }} pipeline hash{{
          report.pipeline_hash_count === 1 ? "" : "es"
        }}
      </span>
    </footer>
  </section>
</template>

<style scoped>
.card {
  background: var(--vf-surface, #1e293b);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  padding: 20px;
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
  color: var(--vf-dark, #f8fafc);
}
.muted {
  font-size: 11px;
  color: var(--vf-light-muted, #94a3b8);
}
.row {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) 80px 200px;
  align-items: center;
  gap: 12px;
  padding: 10px 8px;
  border-top: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.06));
  font-size: 13px;
  color: var(--vf-dark, #f8fafc);
}
.row.head {
  border-top: none;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--vf-muted, #94a3b8);
}
.row.fragile {
  background: rgba(239, 68, 68, 0.08);
}
.bar {
  display: flex;
  gap: 2px;
  height: 14px;
}
.seg {
  border-radius: 3px;
}
.seg.good {
  background: rgba(34, 197, 94, 0.45);
}
.seg.bad {
  background: rgba(239, 68, 68, 0.6);
}
.chips {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.chip {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  color: var(--vf-light-muted, #94a3b8);
  background: rgba(255, 255, 255, 0.05);
}
.chip.ok {
  color: #4ade80;
  background: rgba(34, 197, 94, 0.12);
}
.chip.warn {
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.12);
}
.chip.danger {
  color: #f87171;
  background: rgba(239, 68, 68, 0.14);
}
.notice.danger {
  margin: 8px 0;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
  color: #f87171;
  background: rgba(239, 68, 68, 0.1);
}
</style>
