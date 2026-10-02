<script setup lang="ts">
import type { FeatureItem } from '../../services/featureService'

defineProps<{
  features: FeatureItem[]
}>()
</script>

<template>
  <div class="feature-table-wrapper">
    <div class="feature-table">
      <div class="table-header">
        <span>Feature</span>
        <span>Category</span>
        <span>Measurement</span>
        <span>Purpose</span>
      </div>

      <div v-for="item in features" :key="item.id" class="feature-row">
        <div class="feature-name">
          <div class="feature-icon">{{ item.icon }}</div>
          <div>
            <strong>{{ item.name }}</strong>
            <span>{{ item.code }}</span>
          </div>
        </div>

        <span :class="['category-badge', item.categoryVariant]">
          {{ item.category }}
        </span>

        <span class="measurement">{{ item.measurement }}</span>
        <span class="purpose">{{ item.purpose }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.feature-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.feature-table {
  width: 100%;
  min-width: 680px;
}

.table-header,
.feature-row {
  display: grid;
  grid-template-columns: 1.4fr 0.8fr 0.9fr 2fr;
  gap: 18px;
  align-items: center;
  padding: 14px 22px;
}

.table-header {
  color: var(--vf-light-muted, #a1a1aa);
  background: #fcfcfc;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.feature-row {
  min-height: 76px;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  transition: background 0.18s ease;
}

.feature-row:last-child {
  border-bottom: none;
}

.feature-row:hover {
  background: #fffaf6;
}

.feature-name {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}

.feature-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  color: var(--vf-orange-dark, #ea580c);
  background: var(--vf-orange-soft, #fff7ed);
  font-size: 11px;
  font-weight: 700;
}

.feature-name strong {
  display: block;
  color: var(--vf-text, #27272a);
  font-size: 12px;
  font-weight: 700;
}

.feature-name span {
  display: block;
  margin-top: 3px;
  color: var(--vf-light-muted, #a1a1aa);
  font-size: 10px;
}

.category-badge {
  display: inline-flex;
  width: fit-content;
  padding: 5px 8px;
  border-radius: 5px;
  font-size: 9px;
  font-weight: 700;
}

.category-badge.orange {
  color: var(--vf-orange-dark, #ea580c);
  background: var(--vf-orange-soft, #fff7ed);
}

.category-badge.red {
  color: var(--vf-red, #ef4444);
  background: var(--vf-red-soft, #fef2f2);
}

.category-badge.warm {
  color: #b45309;
  background: #fffbeb;
}

.measurement {
  color: var(--vf-text, #27272a);
  font-size: 11px;
  font-weight: 600;
}

.purpose {
  color: var(--vf-muted, #71717a);
  font-size: 11px;
  line-height: 1.5;
}

@media (max-width: 1000px) {
  .table-header,
  .feature-row {
    grid-template-columns: 1.3fr 0.8fr 0.8fr 1.5fr;
  }
}
</style>