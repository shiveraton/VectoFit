<script setup lang="ts">
interface Props {
  title?: string;
  description?: string;
  buttonText?: string;
}

withDefaults(defineProps<Props>(), {
  title: "No training runs yet",
  description:
    "Configure a dataset and training task to create your first VectoFit model experiment.",
  buttonText: "Configure Training",
});

const emit = defineEmits<{
  (e: "configure"): void;
}>();
</script>

<template>
  <div class="empty-state">
    <div class="empty-illustration">
      <div class="chart-bars">
        <span></span>
        <span></span>
        <span></span>
        <span></span>
      </div>
      <div class="chart-line"></div>
    </div>

    <h3>{{ title }}</h3>
    <p>{{ description }}</p>

    <button class="secondary-button" @click="emit('configure')">
      <span>+</span> {{ buttonText }}
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
  align-items: flex-end;
  justify-content: center;
  gap: 5px;
  width: 62px;
  height: 62px;
  margin-bottom: 18px;
  padding-bottom: 16px;
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 14px;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 5px;
  height: 30px;
}

.chart-bars span {
  width: 6px;
  background: #fb923c;
  border-radius: 2px 2px 0 0;
}

.chart-bars span:nth-child(1) {
  height: 12px;
}
.chart-bars span:nth-child(2) {
  height: 19px;
}
.chart-bars span:nth-child(3) {
  height: 25px;
}
.chart-bars span:nth-child(4) {
  height: 17px;
}

.chart-line {
  position: absolute;
  top: 20px;
  left: 14px;
  width: 34px;
  height: 2px;
  background: var(--vf-gradient);
  transform: rotate(-12deg);
}

.empty-state h3 {
  margin: 0 0 7px;
  color: var(--vf-dark);
  font-size: 16px;
  font-weight: 700;
}

.empty-state p {
  max-width: 390px;
  margin: 0 auto 20px;
  color: var(--vf-light-muted);
  font-size: 12px;
  line-height: 1.65;
}
</style>
