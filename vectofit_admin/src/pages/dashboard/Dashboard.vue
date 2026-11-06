<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useDashboard } from "../../hooks/useDashboard";
import SummaryCard from "../../components/datasets/SummaryCard.vue";

interface Props {
  eyebrowText?: string;
  pageTitle?: string;
  pageDescription?: string;
}

withDefaults(defineProps<Props>(), {
  eyebrowText: "VECTOFIT SYSTEM OVERVIEW",
  pageTitle: "Dashboard",
  pageDescription:
    "Datasets, model versions, and training activity in one research workspace.",
});

const { dashboardCards, currentModel, error, fetchAllDashboardData } = useDashboard();

const isRefreshing = ref(false);
const handleRefresh = async (force = true) => {
  if (isRefreshing.value) return;
  isRefreshing.value = true;
  try { await fetchAllDashboardData(force); }
  finally { isRefreshing.value = false; }
};

const formatMetric = (
  value: unknown,
  options?: { multiplier?: number; suffix?: string; decimals?: number },
): string => {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "N/A";
  }

  const { multiplier = 1, suffix = "", decimals = 1 } = options ?? {};

  return `${(value * multiplier).toFixed(decimals)}${suffix}`;
};

const modelAlgorithm = computed(() => currentModel.value?.algorithm ?? "N/A");

const modelLatency = computed(() =>
  formatMetric(currentModel.value?.metrics?.latencyMs, {
    suffix: " ms",
    decimals: 1,
  }),
);

const modelAccuracy = computed(() =>
  formatMetric(currentModel.value?.metrics?.accuracy, {
    multiplier: 100,
    suffix: "%",
    decimals: 1,
  }),
);

onMounted(() => {
  handleRefresh(false);
});
</script>

<template>
  <div class="dashboard-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          {{ eyebrowText }}
        </div>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageDescription }}</p>
      </div>

      <button class="secondary-button" :disabled="isRefreshing" @click="handleRefresh(true)">
        <span class="button-icon" aria-hidden="true">&#8635;</span> {{ isRefreshing ? "Refreshing..." : "Refresh overview" }}
      </button>
    </header>

    <p v-if="isRefreshing" class="refresh-status" role="status">Updating workspace overview...</p>

    <div v-if="error" class="error-banner" role="alert"><strong>Workspace data could not be fully loaded.</strong> {{ error }} Refresh to try again.</div>
    <section v-else class="summary-grid" :aria-busy="isRefreshing">
      <SummaryCard
        v-for="card in dashboardCards"
        :key="card.label"
        v-bind="card"
      />
    </section>

    <section v-if="!error" class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker"></div>
          <div>
            <h2>Registered Model Overview</h2>
            <p>Model metadata and available performance metrics.</p>
          </div>
        </div>

        <span class="status-badge" :class="{ 'is-active': currentModel }">
          {{ currentModel ? "REGISTERED" : "NO MODEL" }}
        </span>
      </div>

      <div class="card-body">
        <template v-if="currentModel">
          <div class="active-endpoint-details">
            <div class="detail-group">
              <span class="detail-label">Model Name</span>
              <span class="detail-value">{{ currentModel.name }}</span>
            </div>

            <div class="detail-group">
              <span class="detail-label">Version</span>
              <span class="detail-value font-mono">
                {{ currentModel.version }}
              </span>
            </div>

            <div class="detail-group">
              <span class="detail-label">Algorithm</span>
              <span class="detail-value">{{ modelAlgorithm }}</span>
            </div>

            <div class="detail-group">
              <span class="detail-label">p99 Latency</span>
              <span class="detail-value font-mono">
                {{ modelLatency }}
              </span>
            </div>

            <div class="detail-group">
              <span class="detail-label">Accuracy</span>
              <span class="detail-value font-mono">
                {{ modelAccuracy }}
              </span>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="empty-endpoint">
            <h3>No registered model yet</h3>
            <p>Complete a training run, then inspect its evidence in the model registry.</p>
            <RouterLink to="/training" class="secondary-button">Go to training</RouterLink>
          </div>
        </template>
      </div>
    </section>

    <section class="workspace-tasks" aria-labelledby="workspace-tasks-title">
      <div class="tasks-heading"><h2 id="workspace-tasks-title">Research workflow</h2><p>Move from source data to reviewed model evidence.</p></div>
      <RouterLink to="/dataset" class="task-link"><span class="task-number">01</span><div><strong>Prepare your datasets</strong><p>Import recordings, review labels, and check training readiness.</p></div><span aria-hidden="true">&rarr;</span></RouterLink>
      <RouterLink to="/training" class="task-link"><span class="task-number">02</span><div><strong>Configure a training run</strong><p>Choose eligible datasets and inspect the FPPA v2 configuration.</p></div><span aria-hidden="true">&rarr;</span></RouterLink>
      <RouterLink to="/models" class="task-link"><span class="task-number">03</span><div><strong>Review model evidence</strong><p>Compare saved versions, evaluation results, and activation checks.</p></div><span aria-hidden="true">&rarr;</span></RouterLink>
    </section>
  </div>
</template>

<style scoped>

.active-endpoint-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}

.detail-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  color: var(--vf-muted);
}

.detail-value {
  font-size: 14px;
  font-weight: 600;
  overflow-wrap: anywhere;
  color: var(--vf-dark);
}

.empty-endpoint {
  color: var(--vf-muted);
  font-size: 13px;
  text-align: left;
  padding: 8px 0;
}

@media (max-width: 1000px) {
.active-endpoint-details {
    grid-template-columns: repeat(2, 1fr);
  }

}

.refresh-status { margin: -12px 0 16px; color: var(--vf-muted); font-size: 12px; }
.empty-endpoint h3 { margin: 0 0 8px; color: var(--vf-dark); font-size: 16px; font-weight: 600; }
.empty-endpoint p { margin: 0 0 20px; }
.workspace-tasks { margin-top: 32px; }
.tasks-heading { margin-bottom: 12px; }
.tasks-heading h2 { margin: 0 0 4px; color: var(--vf-dark); font-size: 16px; font-weight: 600; }
.tasks-heading p { margin: 0; color: var(--vf-muted); font-size: 13px; }
.task-link { display: flex; align-items: center; gap: 20px; padding: 20px 0; border-bottom: 1px solid var(--vf-border); color: var(--vf-text); text-decoration: none; }
.task-link > div { flex: 1; }
.task-link strong { font-size: 14px; font-weight: 600; }
.task-link p { margin: 4px 0 0; color: var(--vf-muted); font-size: 13px; }
.task-number { color: var(--vf-muted); font-size: 12px; font-variant-numeric: tabular-nums; }
.task-link:hover strong { color: var(--vf-orange); text-decoration: underline; text-underline-offset: 3px; }
@media (max-width: 600px) { .active-endpoint-details { grid-template-columns: 1fr; } .task-link { gap: 12px; } }
</style>
