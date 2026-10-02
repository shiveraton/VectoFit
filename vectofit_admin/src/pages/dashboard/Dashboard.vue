<script setup lang="ts">
import { onMounted } from "vue";
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
    "Real-time overview of biomechanical datasets, registered models, live active endpoints, and running training jobs.",
});

const { dashboardCards, activeModel, fetchAllDashboardData } = useDashboard();

const handleRefresh = () => {
  fetchAllDashboardData();
};

onMounted(() => {
  fetchAllDashboardData();
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

      <button class="secondary-button" @click="handleRefresh">
        <span class="button-icon">↻</span> Refresh Metrics
      </button>
    </header>

    <section class="summary-grid">
      <SummaryCard
        v-for="card in dashboardCards"
        :key="card.label"
        v-bind="card"
      />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker"></div>
          <div>
            <h2>Active Production Endpoint</h2>
            <p>Live model handling movement vector inference traffic.</p>
          </div>
        </div>
        <span class="status-badge" :class="{ 'is-active': activeModel }">
          {{ activeModel ? "ONLINE" : "INACTIVE" }}
        </span>
      </div>

      <div class="card-body">
        <template v-if="activeModel">
          <div class="active-endpoint-details">
            <div class="detail-group">
              <span class="detail-label">Model Architecture</span>
              <span class="detail-value">{{ activeModel.modelName }}</span>
            </div>
            <div class="detail-group">
              <span class="detail-label">Active Version</span>
              <span class="detail-value font-mono">{{
                activeModel.version
              }}</span>
            </div>
            <div class="detail-group">
              <span class="detail-label">Framework</span>
              <span class="detail-value">{{ activeModel.framework }}</span>
            </div>
            <div class="detail-group">
              <span class="detail-label">p99 Latency</span>
              <span class="detail-value font-mono"
                >{{ activeModel.latencyMs }} ms</span
              >
            </div>
            <div class="detail-group">
              <span class="detail-label">Posture Precision</span>
              <span class="detail-value font-mono">
                {{ (activeModel.accuracy * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="empty-endpoint">
            <p>No model version currently deployed to production.</p>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dashboard-page {
  min-height: 100%;
  padding: 32px;
  background: var(--vf-background);
  font-family: "Segoe UI", Arial, sans-serif;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 28px;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
  color: var(--vf-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.eyebrow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--vf-orange);
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.12);
}

.page-header h1 {
  margin: 0 0 5px;
  color: var(--vf-dark);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.page-header p {
  margin: 0;
  color: var(--vf-muted);
  font-size: 13px;
}

.secondary-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--vf-border-light);
  border-radius: 6px;
  background: #ffffff;
  color: var(--vf-dark);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 24px;
}

.content-card {
  background: #ffffff;
  border: 1px solid var(--vf-border-light);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--vf-border-light);
}

.section-title-row {
  display: flex;
  align-items: flex-start;
  gap: 9px;
}

.section-marker {
  width: 3px;
  height: 17px;
  margin-top: 1px;
  border-radius: 4px;
  background: var(--vf-gradient);
}

.section-header h2 {
  margin: 0;
  color: var(--vf-dark);
  font-size: 15px;
  font-weight: 700;
}

.section-header p {
  margin: 3px 0 0;
  color: var(--vf-light-muted);
  font-size: 11px;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 10px;
  font-weight: 700;
}

.status-badge.is-active {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
}

.card-body {
  padding: 22px;
}

.active-endpoint-details {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.detail-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 11px;
  color: var(--vf-muted);
}

.detail-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--vf-dark);
}

.font-mono {
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.empty-endpoint {
  color: var(--vf-muted);
  font-size: 13px;
  text-align: center;
  padding: 12px 0;
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .active-endpoint-details {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
