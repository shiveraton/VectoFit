<script setup lang="ts">
import { computed } from "vue";
import type { ModelCard } from "../../services/modelService";

const props = defineProps<{ card: ModelCard }>();

const statusLabel = computed(() => {
  switch (props.card.status) {
    case "ready":
      return "READY FOR ACTIVATION";
    case "warning":
      return "READY WITH WARNINGS";
    case "blocked":
      return "ACTIVATION BLOCKED";
    default:
      return String(props.card.status).toUpperCase();
  }
});

const targetLabel = computed(() => {
  return props.card.prediction_target === "knee_alignment"
    ? "Frontal-plane knee alignment"
    : "Unsupported model setup";
});

const classLabels = computed(() =>
  Object.entries(props.card.class_mapping)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([index, label]) => ({ index, label })),
);

const originEntries = computed(() =>
  Object.entries(props.card.data_provenance.label_origin_counts).sort(([a], [b]) =>
    a.localeCompare(b),
  ),
);

const shortHash = computed(() => {
  const hash = props.card.generated_from.manifest_sha256;
  return hash ? `${hash.slice(0, 12)}…` : "not recorded";
});

const checkStatusLabel = (status: string) => {
  if (status === "pass") return "Pass";
  if (status === "warn") return "Warning";
  return "Blocked";
};
</script>

<template>
  <section class="content-card model-card">
    <div class="section-header">
      <div class="section-title-row">
        <div class="section-marker"></div>

        <div>
          <h2>Model Card &amp; Activation Readiness</h2>
          <p>
            Evidence recorded with this version. Activation is gated by the
            checks below.
          </p>
        </div>
      </div>

      <span class="card-status" :class="card.status">
        {{ statusLabel }}
      </span>
    </div>

    <div class="card-body">
      <p class="readiness-summary">
        <strong>
          {{ card.activation.allowed ? "Eligible" : "Not eligible" }} for
          inference
        </strong>
        — {{ card.summary.passed_checks }} of
        {{ card.summary.total_checks }} checks pass,
        {{ card.summary.warning_checks }} warning(s),
        {{ card.summary.failed_checks }} blocker(s).
      </p>

      <div v-if="card.activation.blockers.length" class="blocker-panel">
        <strong>Resolve these before activating</strong>
        <ul>
          <li v-for="blocker in card.activation.blockers" :key="blocker.code">
            <span>{{ blocker.detail }}</span>
            <small v-if="blocker.remediation">{{ blocker.remediation }}</small>
          </li>
        </ul>
      </div>

      <div class="metadata-strip">
        <div>
          <span>Prediction target</span>
          <strong>{{ targetLabel }}</strong>
        </div>
        <div>
          <span>Camera angle</span>
          <strong>{{ card.view_angle || "not recorded" }}</strong>
        </div>
        <div>
          <span>Held-out test samples</span>
          <strong>{{ card.held_out_test_count }}</strong>
        </div>
        <div>
          <span>Participants in manifest</span>
          <strong>{{ card.data_provenance.participant_count }}</strong>
        </div>
        <div>
          <span>Manifest hash</span>
          <strong :title="card.generated_from.manifest_sha256 ?? ''">
            {{ shortHash }}
          </strong>
        </div>
        <div>
          <span>Evaluation scope</span>
          <strong>{{ card.evaluation_scope.replaceAll("_", " ") }}</strong>
        </div>
      </div>

      <div class="card-columns">
        <div>
          <h3>Checks</h3>
          <ul class="check-list">
            <li v-for="check in card.checks" :key="check.code" class="check-row">
              <span class="check-indicator" :class="check.status" aria-hidden="true">
                {{ check.status === "pass" ? "✓" : check.status === "warn" ? "!" : "×" }}
              </span>
              <div>
                <strong>
                  {{ check.label }}
                  <small class="check-status-text" :class="check.status">
                    {{ checkStatusLabel(check.status) }}
                  </small>
                </strong>
                <p>{{ check.detail }}</p>
                <p v-if="check.remediation && check.status !== 'pass'" class="remediation">
                  {{ check.remediation }}
                </p>
              </div>
            </li>
          </ul>
        </div>

        <div class="side-column">
          <h3>Class labels</h3>
          <div v-if="classLabels.length" class="class-labels">
            <span v-for="entry in classLabels" :key="entry.index" class="class-chip">
              <small>{{ entry.index }}</small>
              {{ entry.label }}
            </span>
          </div>
          <p v-else class="muted-note">
            No explicit class ordering was recorded for this model.
          </p>

          <h3>Label provenance</h3>
          <div v-if="originEntries.length" class="origin-list">
            <div v-for="[origin, count] in originEntries" :key="origin">
              <span>{{ origin.replaceAll("_", " ") }}</span>
              <strong>{{ count }}</strong>
            </div>
          </div>
          <p v-else class="muted-note">
            The manifest has no per-sample label-origin records.
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.model-card {
  margin-bottom: 18px;
}

.card-status {
  display: inline-flex;
  flex-shrink: 0;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.card-status.ready {
  background: #f0fdf4;
  color: #15803d;
}

.card-status.warning {
  background: #fffbeb;
  color: #b45309;
}

.card-status.blocked {
  background: #fef2f2;
  color: #b91c1c;
}

.card-body {
  padding: 18px 20px 20px;
}

.readiness-summary {
  margin: 0 0 15px;
  color: var(--vf-muted);
  font-size: 13px;
  line-height: 1.6;
}

.readiness-summary strong {
  color: var(--vf-dark);
}

.blocker-panel {
  margin-bottom: 16px;
  padding: 13px 14px;
  border: 1px solid #fecaca;
  border-radius: 9px;
  background: #fef2f2;
  color: #991b1b;
  font-size: 13px;
  line-height: 1.6;
}

.blocker-panel > strong {
  display: block;
  margin-bottom: 7px;
  font-size: 13px;
}

.blocker-panel ul {
  margin: 0;
  padding-left: 18px;
}

.blocker-panel li + li {
  margin-top: 7px;
}

.blocker-panel small {
  display: block;
  margin-top: 3px;
  color: #b91c1c;
  font-size: 12px;
}

.metadata-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  overflow: hidden;
  border: 1px solid var(--vf-border-light);
  border-radius: 9px;
  background: var(--vf-border-light);
}

.metadata-strip > div {
  min-width: 0;
  padding: 12px 13px;
  background: #fff;
}

.metadata-strip span,
.metadata-strip strong {
  display: block;
}

.metadata-strip span {
  color: var(--vf-muted);
  font-size: 11px;
}

.metadata-strip strong {
  margin-top: 5px;
  overflow-wrap: anywhere;
  color: var(--vf-dark);
  font-size: 13px;
}

.card-columns {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr);
  gap: 22px;
  margin-top: 20px;
}

.card-columns h3 {
  margin: 0 0 10px;
  color: var(--vf-dark);
  font-size: 13px;
}

.check-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.check-row {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 9px 10px;
  border: 1px solid var(--vf-border-light);
  border-radius: 8px;
  background: #fff;
}

.check-indicator {
  display: grid;
  width: 17px;
  height: 17px;
  flex-shrink: 0;
  place-items: center;
  margin-top: 1px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 800;
}

.check-indicator.pass {
  background: #f0fdf4;
  color: #15803d;
}

.check-indicator.warn {
  background: #fffbeb;
  color: #b45309;
}

.check-indicator.fail {
  background: #fef2f2;
  color: #b91c1c;
}

.check-row strong {
  display: block;
  color: var(--vf-dark);
  font-size: 10.5px;
}

.check-status-text {
  margin-left: 5px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.check-status-text.pass {
  color: #15803d;
}

.check-status-text.warn {
  color: #b45309;
}

.check-status-text.fail {
  color: #b91c1c;
}

.check-row p {
  margin: 3px 0 0;
  color: var(--vf-muted);
  font-size: 9.5px;
  line-height: 1.55;
}

.check-row p.remediation {
  color: #9a3412;
}

.side-column h3:not(:first-child) {
  margin-top: 18px;
}

.class-labels {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.class-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border: 1px solid var(--vf-border-light);
  border-radius: 999px;
  background: #fafafa;
  color: var(--vf-dark);
  font-size: 12px;
}

.class-chip small {
  display: grid;
  width: 15px;
  height: 15px;
  place-items: center;
  border-radius: 50%;
  background: #fff;
  color: var(--vf-muted);
  font-size: 12px;
  font-weight: 700;
}

.origin-list {
  display: grid;
  gap: 6px;
}

.origin-list > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 9px;
  border: 1px solid var(--vf-border-light);
  border-radius: 7px;
  background: #fafafa;
  font-size: 12px;
}

.origin-list span {
  color: var(--vf-muted);
  text-transform: capitalize;
}

.origin-list strong {
  color: var(--vf-dark);
}

.muted-note {
  margin: 0;
  color: var(--vf-muted);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 1000px) {
  .metadata-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .card-columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 650px) {
  .metadata-strip {
    grid-template-columns: 1fr;
  }
}
</style>
