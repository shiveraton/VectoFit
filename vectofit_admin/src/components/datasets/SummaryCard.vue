<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  description: string
  icon: string
  variant?: 'samples' | 'correct' | 'incorrect' | 'version'
  statusIcon?: boolean
}>()
</script>

<template>
  <div class="summary-card">
    <div class="summary-card-top">
      <span class="summary-label">{{ label }}</span>
      <div 
        :class="[
          'summary-icon', 
          variant ? `${variant}-icon` : 'samples-icon',
          { 'status-icon': statusIcon }
        ]"
      >
        {{ icon }}
      </div>
    </div>
    <strong class="summary-value">{{ value }}</strong>
    <span class="summary-description">{{ description }}</span>
  </div>
</template>

<style scoped>
.summary-card {
  position: relative;
  min-height: 130px;
  padding: 18px;
  overflow: hidden;
  background: var(--vf-surface, #ffffff);
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(24, 24, 27, 0.025);
}

.summary-card::after {
  position: absolute;
  right: -28px;
  bottom: -32px;
  width: 90px;
  height: 90px;
  content: "";
  border-radius: 50%;
  background: var(--vf-orange-soft, #fff7ed);
}

.summary-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-label {
  color: var(--vf-muted, #71717a);
  font-size: 12px;
  font-weight: 600;
}

.summary-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 700;
}

.samples-icon,
.version-icon {
  color: var(--vf-orange-dark, #ea580c);
  background: var(--vf-orange-soft, #fff7ed);
}

.correct-icon {
  color: #b45309;
  background: #fffbeb;
}

.incorrect-icon,
.status-icon {
  color: var(--vf-red, #ef4444);
  background: var(--vf-red-soft, #fef2f2);
}

.summary-value {
  display: block;
  margin: 15px 0 3px;
  color: var(--vf-dark, #18181b);
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
}

.summary-description {
  color: var(--vf-light-muted, #a1a1aa);
  font-size: 11px;
}
</style>