<script setup lang="ts">
import { ref } from "vue";

withDefaults(
  defineProps<{
    title: string;
    value: string;
    question: string;
    description: string;
    interpretation: string;
    variant?: "default" | "primary";
  }>(),
  { variant: "default" },
);

const showInfo = ref(false);
</script>

<template>
  <article :class="['metric-card', { primary: variant === 'primary' }]">
    <header class="metric-header">
      <span>{{ title }}</span>
      <button
        type="button"
        class="info-button"
        :aria-expanded="showInfo"
        :aria-label="`Explain ${title}`"
        @click="showInfo = !showInfo"
      >
        ?
      </button>
    </header>

    <strong class="metric-value">{{ value }}</strong>

    <p class="metric-question">{{ question }}</p>

    <Transition name="metric-fade">
      <div v-if="showInfo" class="metric-help">
        <p>{{ description }}</p>
        <span>{{ interpretation }}</span>
      </div>
    </Transition>
  </article>
</template>

<style scoped>
.metric-card {
  min-width: 0;
  padding: 15px;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 10px;
}

.metric-card.primary {
  background: #fffaf6;
  border-color: #fed7aa;
}

.metric-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.metric-header > span {
  color: var(--vf-muted);
  font-size: 12px;
  font-weight: 700;
}

.info-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 19px;
  height: 19px;
  color: var(--vf-muted);
  background: #fafafa;
  border: 1px solid var(--vf-border);
  border-radius: 50%;
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
}

.info-button:hover,
.info-button[aria-expanded="true"] {
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border-color: #fed7aa;
}

.metric-value {
  display: block;
  margin-top: 14px;
  color: var(--vf-dark);
  font-size: 24px;
  line-height: 1;
  letter-spacing: -0.02em;
}

.metric-question {
  margin: 9px 0 0;
  color: var(--vf-light-muted);
  font-size: 11px;
  line-height: 1.5;
}

.metric-help {
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px solid var(--vf-border-light);
  color: var(--vf-muted);
  font-size: 11px;
  line-height: 1.5;
}

.metric-help p {
  margin: 0;
}

.metric-help span {
  display: block;
  margin-top: 5px;
  color: var(--vf-orange-dark);
}

.metric-fade-enter-active,
.metric-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.metric-fade-enter-from,
.metric-fade-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}
</style>
