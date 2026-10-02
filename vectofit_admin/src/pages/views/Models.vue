<script setup lang="ts">
import { useModels } from "../../hooks/useModels.ts";
import type { ModelVersion } from "../../services/modelService.ts";
import SummaryCard from "../../components/datasets/SummaryCard.vue";
import ModelsTable from "../../components/models/ModelsTable.vue";
import ModelsEmptyState from "../../components/models/ModelsEmptyState.vue";
import ModelsWorkflow from "../../components/models/ModelsWorkflow.vue";
import DeployModal from "../../components/models/DeployModal.vue";

interface Props {
  eyebrowText?: string;
  pageTitle?: string;
  pageDescription?: string;
  actionButtonText?: string;
}

withDefaults(defineProps<Props>(), {
  eyebrowText: "VECTOFIT MODEL REGISTRY & DEPLOYMENT",
  pageTitle: "Models",
  pageDescription:
    "Manage model artifacts, inspect version benchmarks, and provision real-time inference endpoints.",
});

const emit = defineEmits<{
  (e: "register-model"): void;
  (e: "deploy-started", modelId: string, versionId: string): void;
}>();

const {
  models,
  isLoading,
  summaryCards,
  workflowSteps,
  selectedTarget,
  isDeployModalOpen,
  openDeployModal,
  closeDeployModal,
  handleDeploy,
  handleUndeploy,
} = useModels();

const handleRegisterModel = () => {
  emit("register-model");
};

const onOpenDeploy = (modelId: string, version: ModelVersion) => {
  openDeployModal(modelId, version);
};

const onUndeploy = (modelId: string, version: ModelVersion) => {
  handleUndeploy(modelId, version);
};

const onConfirmDeploy = async (config: {
  environment: "staging" | "production";
  minReplicas: number;
  maxReplicas: number;
}) => {
  if (selectedTarget.value) {
    const { modelId, version } = selectedTarget.value;
    await handleDeploy(config);
    emit("deploy-started", modelId, version.id);
  }
};
</script>

<template>
  <div class="models-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          {{ eyebrowText }}
        </div>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageDescription }}</p>
      </div>
    </header>

    <section class="summary-grid">
      <SummaryCard
        v-for="card in summaryCards"
        :key="card.label"
        v-bind="card"
      />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <div>
              <h2>Model Registry & Deployments</h2>
              <p>
                Registered model artifacts, version histories, and active
                inference endpoints.
              </p>
            </div>
          </div>
        </div>
        <span class="status-badge">
          {{
            models.length > 0
              ? `${models.length} MODELS REGISTERED`
              : "NO MODELS"
          }}
        </span>
      </div>

      <ModelsTable
        v-if="models.length > 0"
        :models="models"
        :is-loading="isLoading"
        @open-deploy="onOpenDeploy"
        @undeploy="onUndeploy"
      />
      <ModelsEmptyState v-else @register="handleRegisterModel" />
    </section>

    <section class="content-card">
      <div class="section-header">
        <div>
          <div class="section-title-row">
            <div class="section-marker"></div>
            <div>
              <h2>Model Lifecycle & Deployment Process</h2>
              <p>
                Standardized pipeline for registering, benchmarking, and hosting
                biomechanical models.
              </p>
            </div>
          </div>
        </div>
      </div>

      <ModelsWorkflow :steps="workflowSteps" />
    </section>

    <DeployModal
      :is-open="isDeployModalOpen"
      :target="selectedTarget"
      @close="closeDeployModal"
      @confirm="onConfirmDeploy"
    />
  </div>
</template>

<style scoped>
.models-page {
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

.page-heading {
  display: flex;
  flex-direction: column;
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
  text-transform: uppercase;
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

.button-icon {
  font-size: 15px;
  font-weight: 700;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.content-card {
  background: #ffffff;
  border: 1px solid var(--vf-border-light);
  border-radius: 10px;
  margin-bottom: 24px;
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
  flex-shrink: 0;
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
  background: rgba(249, 115, 22, 0.08);
  color: var(--vf-orange);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 700px) {
  .models-page {
    padding: 20px;
  }
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 18px;
  }
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
