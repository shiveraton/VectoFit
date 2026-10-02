<script setup lang="ts">
import type { FeatureGroup } from '../../services/featureService'

defineProps<{
  groups: FeatureGroup[]
}>()
</script>

<template>
  <div class="group-grid">
    <div v-for="group in groups" :key="group.id" class="group-card">
      <div :class="['group-icon', `${group.iconVariant}-icon`]">
        {{ group.icon }}
      </div>

      <div class="group-content">
        <span class="group-label">{{ group.label }}</span>
        <h3>{{ group.title }}</h3>
        <p>{{ group.description }}</p>

        <div class="group-features">
          <span v-for="tag in group.tags" :key="tag">{{ tag }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.group-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
}

.group-card {
  display: flex;
  gap: 15px;
  padding: 22px;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  transition: background 0.18s ease;
}

.group-card:hover {
  background: #fffaf6;
}

.group-card:nth-child(odd) {
  border-right: 1px solid var(--vf-border-light, #f1f1f2);
}

.group-card:nth-last-child(-n + 2) {
  border-bottom: none;
}

.group-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 700;
}

.orange-icon {
  color: var(--vf-orange-dark, #ea580c);
  background: var(--vf-orange-soft, #fff7ed);
}

.red-icon {
  color: var(--vf-red, #ef4444);
  background: var(--vf-red-soft, #fef2f2);
}

.warm-icon {
  color: #b45309;
  background: #fffbeb;
}

.gradient-icon {
  color: #ffffff;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
}

.group-content {
  min-width: 0;
}

.group-label {
  color: var(--vf-light-muted, #a1a1aa);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.group-content h3 {
  margin: 5px 0 7px;
  color: var(--vf-dark, #18181b);
  font-size: 14px;
  font-weight: 700;
}

.group-content p {
  margin: 0 0 12px;
  color: var(--vf-muted, #71717a);
  font-size: 11px;
  line-height: 1.55;
}

.group-features {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.group-features span {
  padding: 4px 7px;
  color: var(--vf-text, #27272a);
  background: #f4f4f5;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 600;
}

@media (max-width: 700px) {
  .group-grid {
    grid-template-columns: 1fr;
  }

  .group-card:nth-child(odd) {
    border-right: none;
  }

  .group-card:nth-last-child(-n + 2) {
    border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  }

  .group-card:last-child {
    border-bottom: none;
  }
}
</style>