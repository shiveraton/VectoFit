<script setup lang="ts">
import type { WorkflowStep } from "../../services/trainingService";

defineProps<{
  steps: WorkflowStep[];
}>();
</script>

<template>
  <div class="workflow">
    <template v-for="(step, index) in steps" :key="step.number">
      <div :class="['workflow-step', { active: step.active }]">
        <div class="workflow-number">
          {{ step.number }}
        </div>

        <strong>{{ step.title }}</strong>

        <span>{{ step.subtitle }}</span>
      </div>

      <div v-if="index < steps.length - 1" class="workflow-line"></div>
    </template>
  </div>
</template>

<style scoped>
.workflow {
  display: flex;
  align-items: center;
  padding: 26px 28px;
}

.workflow-step {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;
}

.workflow-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-bottom: 3px;
  color: var(--vf-muted);
  background: #f4f4f5;
  border: 1px solid var(--vf-border);
  border-radius: 7px;
  font-size: 9px;
  font-weight: 700;
}

.workflow-step.active .workflow-number {
  color: #ffffff;
  background: var(--vf-gradient);
  border-color: transparent;
}

.workflow-step strong {
  color: var(--vf-text);
  font-size: 11px;
  font-weight: 700;
}

.workflow-step span {
  color: var(--vf-light-muted);
  font-size: 9px;
}

.workflow-line {
  width: 45px;
  height: 1px;
  margin: 0 12px 26px;
  background: #fed7aa;
}

@media (max-width: 800px) {
  .workflow {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .workflow-step {
    width: 100%;
  }

  .workflow-line {
    width: 1px;
    height: 20px;
    margin: 0 0 0 14px;
  }
}
</style>
