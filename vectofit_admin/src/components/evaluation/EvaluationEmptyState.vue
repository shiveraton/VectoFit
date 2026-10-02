<script setup lang="ts">
const emit = defineEmits<{
  (e: "configure"): void;
}>();
</script>

<template>
  <div class="empty-state-container">
    <div class="icon-badge">
      <svg
        class="empty-icon"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    </div>

    <h3 class="empty-title">No Evaluation Runs Found</h3>
    <p class="empty-description">
      There are currently no model evaluations recorded for this workspace.
      Select a target model checkpoint and reference dataset above to trigger
      your first biomechanical evaluation run.
    </p>

    <button class="primary-button" @click="emit('configure')">
      <span class="button-icon">+</span> Configure New Evaluation
    </button>
  </div>
</template>

<style scoped>
.empty-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 56px 24px;
  text-align: center;
}

.icon-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: 18px;
  border-radius: 16px;
  background: rgba(249, 115, 22, 0.08);
  border: 1px solid rgba(249, 115, 22, 0.2);
  color: var(--vf-orange, #f97316);
  box-shadow: 0 0 20px rgba(249, 115, 22, 0.08);
}

.empty-icon {
  width: 26px;
  height: 26px;
}

.empty-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--vf-dark, #f8fafc);
  letter-spacing: -0.01em;
}

.empty-description {
  max-width: 440px;
  margin: 0 0 22px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--vf-light-muted, #94a3b8);
}

.primary-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  background: var(--vf-orange, #f97316);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 2px 10px rgba(249, 115, 22, 0.2);
}

.primary-button:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(249, 115, 22, 0.3);
}

.button-icon {
  font-size: 14px;
  font-weight: 800;
}
</style>
