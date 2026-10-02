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
    <div class="empty-illustration">
      <div class="folder-icon">
        <div class="folder-tab"></div>
        <div class="folder-body"></div>
      </div>
    </div>

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

.empty-illustration {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 62px;
  height: 62px;
  margin-bottom: 18px;
  background: var(--vf-orange-soft, #fff7ed);
  border: 1px solid #fed7aa;
  border-radius: 14px;
}

.folder-icon {
  position: relative;
  width: 28px;
  height: 22px;
}

.folder-tab {
  position: absolute;
  top: 0;
  left: 0;
  width: 10px;
  height: 4px;
  background: #fb923c;
  border-radius: 2px 2px 0 0;
}

.folder-body {
  position: absolute;
  bottom: 0;
  width: 100%;
  height: 18px;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  border-radius: 3px 5px 4px 4px;
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
  color: var(--vf-light-muted, #a1a1aa);
  font-size: 12px;
  line-height: 1.65;
}

.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 14px;
  color: var(--vf-orange-dark, #ea580c);
  background: var(--vf-orange-soft, #fff7ed);
  border: 1px solid #fed7aa;
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.secondary-button:hover {
  background: #ffedd5;
  border-color: #fdba74;
}

.button-icon {
  font-size: 16px;
  font-weight: 400;
  line-height: 1;
}
</style>