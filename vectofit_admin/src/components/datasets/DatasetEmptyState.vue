<script setup lang="ts">
defineProps<{
  title?: string
  description?: string
  buttonLabel?: string
}>()

const emit = defineEmits<{
  (e: 'action'): void
}>()
</script>

<template>
  <div class="empty-state">


    <h3>{{ title || 'No datasets available' }}</h3>

    <p>
      {{ description || 'Create or upload your first dataset to start defining biomechanical squat features and training models.' }}
    </p>

    <button class="secondary-button" @click="emit('action')">
      <span class="button-icon">+</span>
      {{ buttonLabel || 'Create Dataset' }}
    </button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 52px 20px 56px;
  text-align: center;
}









.empty-state h3 {
  margin: 0 0 7px;
  color: var(--vf-dark, #18181b);
  font-size: 16px;
  font-weight: 700;
}

.empty-state p {
  max-width: 390px;
  margin: 0 auto 20px;
  color: var(--vf-muted);
  font-size: 14px;
  line-height: 1.65;
}





.button-icon {
  font-size: 16px;
  font-weight: 400;
  line-height: 1;
}
</style>