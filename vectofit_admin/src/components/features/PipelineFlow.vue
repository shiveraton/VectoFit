<script setup lang="ts">
import type { PipelineStep } from '../../services/featureService'

defineProps<{
  steps: PipelineStep[]
}>()
</script>

<template>
  <div class="pipeline">
    <template v-for="(step, index) in steps" :key="step.number">
      <div class="pipeline-step">
        <div class="pipeline-number">{{ step.number }}</div>
        <strong>{{ step.title }}</strong>
        <span>{{ step.subtitle }}</span>
      </div>

      <div v-if="index < steps.length - 1" class="pipeline-line"></div>
    </template>
  </div>
</template>

<style scoped>
.pipeline {
  display: flex;
  align-items: center;
  padding: 26px 28px;
}

.pipeline-step {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;
}

.pipeline-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-bottom: 3px;
  color: #ffffff;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  border-radius: 7px;
  font-size: 9px;
  font-weight: 700;
}

.pipeline-step strong {
  color: var(--vf-text, #27272a);
  font-size: 11px;
  font-weight: 700;
}

.pipeline-step span {
  color: var(--vf-light-muted, #a1a1aa);
  font-size: 9px;
}

.pipeline-line {
  width: 45px;
  height: 1px;
  margin: 0 12px 26px;
  background: #fed7aa;
}

@media (max-width: 800px) {
  .pipeline {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .pipeline-step {
    width: 100%;
  }

  .pipeline-line {
    width: 1px;
    height: 20px;
    margin: 0 0 0 14px;
  }
}
</style>