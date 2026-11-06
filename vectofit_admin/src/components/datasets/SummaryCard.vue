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
    <span class="summary-label">{{ label }}</span>
    <strong class="summary-value">{{ value }}</strong>
    <span class="summary-description">{{ description }}</span>
  </div>
</template>
