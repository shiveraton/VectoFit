<script setup lang="ts">
export interface WorkflowStep {
  stepNumber: number;
  title: string;
  description: string;
  status: "completed" | "active" | "pending";
}

defineProps<{
  steps: WorkflowStep[];
}>();
</script>

<template>
  <div class="workflow-container">
    <div class="workflow-steps">
      <div
        v-for="(step, index) in steps"
        :key="step.stepNumber"
        class="workflow-step"
        :class="`status-${step.status}`"
      >
        <div class="step-header">
          <div class="step-badge">
            <span v-if="step.status === 'completed'" class="step-check">✓</span>
            <span v-else>{{ step.stepNumber }}</span>
          </div>

          <span class="step-status-tag">
            {{ step.status }}
          </span>
        </div>

        <div class="step-body">
          <h3 class="step-title">{{ step.title }}</h3>
          <p class="step-description">{{ step.description }}</p>
        </div>

        <div v-if="index < steps.length - 1" class="step-connector"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.workflow-container {
  padding: 24px;
}

.workflow-steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  position: relative;
}

.workflow-step {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 20px;
  background: var(--vf-surface, #1e293b);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  transition: all 0.2s ease;
}

.workflow-step.status-active {
  border-color: var(--vf-orange, #f97316);
  background: rgba(249, 115, 22, 0.04);
  box-shadow: 0 0 0 1px rgba(249, 115, 22, 0.2);
}

.workflow-step.status-completed {
  border-color: rgba(34, 197, 94, 0.3);
}

.workflow-step.status-pending {
  opacity: 0.65;
}

.step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.step-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  background: var(--vf-surface-muted, #334155);
  color: var(--vf-muted, #94a3b8);
}

.status-active .step-badge {
  background: var(--vf-orange, #f97316);
  color: #ffffff;
}

.status-completed .step-badge {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.step-check {
  font-size: 13px;
  font-weight: 800;
}

.step-status-tag {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--vf-muted, #94a3b8);
  background: rgba(255, 255, 255, 0.05);
}

.status-active .step-status-tag {
  color: var(--vf-orange, #f97316);
  background: rgba(249, 115, 22, 0.12);
}

.status-completed .step-status-tag {
  color: #4ade80;
  background: rgba(34, 197, 94, 0.12);
}

.step-title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--vf-dark, #f8fafc);
  line-height: 1.3;
}

.step-description {
  margin: 0;
  font-size: 12px;
  color: var(--vf-light-muted, #94a3b8);
  line-height: 1.5;
}

@media (max-width: 1024px) {
  .workflow-steps {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .workflow-steps {
    grid-template-columns: 1fr;
  }
}
</style>
