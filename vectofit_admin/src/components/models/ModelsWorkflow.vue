<script setup lang="ts">
export interface WorkflowStep {
  step: string;
  title: string;
  description: string;
}

defineProps<{
  steps: WorkflowStep[];
}>();
</script>

<template>
  <div class="workflow-grid">
    <div v-for="step in steps" :key="step.step" class="workflow-card">
      <div class="step-badge-row">
        <span class="step-badge">{{ step.step }}</span>
        <span class="step-connector"></span>
      </div>
      <h3 class="step-title">{{ step.title }}</h3>
      <p class="step-description">{{ step.description }}</p>
    </div>
  </div>
</template>

<style scoped>
.workflow-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 22px;
}

.workflow-card {
  display: flex;
  flex-direction: column;
  padding: 18px;
  border: 1px solid var(--vf-border-light);
  border-radius: 8px;
  background: #fafafa;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.workflow-card:hover {
  border-color: rgba(249, 115, 22, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}

.step-badge-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.step-badge {
  font-family: monospace;
  font-size: 13px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(249, 115, 22, 0.12);
  color: var(--vf-orange);
}

.step-connector {
  flex-grow: 1;
  height: 1px;
  background: var(--vf-border-light);
}

.step-title {
  margin: 0 0 6px;
  color: var(--vf-dark);
  font-size: 13px;
  font-weight: 700;
}

.step-description {
  margin: 0;
  color: var(--vf-muted);
  font-size: 13px;
  line-height: 1.5;
}

@media (max-width: 1000px) {
  .workflow-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .workflow-grid {
    grid-template-columns: 1fr;
  }
}
</style>
