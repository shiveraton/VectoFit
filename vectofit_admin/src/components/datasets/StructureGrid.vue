<script setup lang="ts">
export interface StructureItem {
  id: string
  icon: string
  iconVariant: 'feature' | 'target' | 'error' | 'sample'
  title: string
  value: string
}

withDefaults(
  defineProps<{
    items?: StructureItem[]
  }>(),
  {
    items: () => [
      {
        id: 'features',
        icon: 'F',
        iconVariant: 'feature',
        title: 'Features',
        value: 'ROM, asymmetry, angles, velocity'
      },
      {
        id: 'primary-target',
        icon: 'C',
        iconVariant: 'target',
        title: 'Primary Target',
        value: 'Correct / Incorrect'
      },
      {
        id: 'secondary-target',
        icon: 'E',
        iconVariant: 'error',
        title: 'Secondary Targets',
        value: 'Biomechanical error labels'
      },
      {
        id: 'sample-unit',
        icon: 'R',
        iconVariant: 'sample',
        title: 'Sample Unit',
        value: 'One completed squat repetition'
      }
    ]
  }
)
</script>

<template>
  <div class="structure-grid">
    <div v-for="item in items" :key="item.id" class="structure-item">
      <div :class="['structure-icon', `${item.iconVariant}-icon`]">
        {{ item.icon }}
      </div>

      <div class="structure-content">
        <span class="structure-title">{{ item.title }}</span>
        <span class="structure-value">{{ item.value }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.structure-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
}

.structure-item {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 86px;
  padding: 17px 22px;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  transition: background 0.18s ease;
}

.structure-item:hover {
  background: #fffaf6;
}

.structure-item:nth-child(odd) {
  border-right: 1px solid var(--vf-border-light, #f1f1f2);
}

.structure-item:nth-last-child(-n + 2) {
  border-bottom: none;
}

.structure-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
}

.feature-icon,
.sample-icon {
  color: var(--vf-orange-dark, #ea580c);
  background: var(--vf-orange-soft, #fff7ed);
}

.target-icon {
  color: #b45309;
  background: #fffbeb;
}

.error-icon {
  color: var(--vf-red, #ef4444);
  background: var(--vf-red-soft, #fef2f2);
}

.structure-content {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.structure-title {
  color: var(--vf-muted, #71717a);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.structure-value {
  color: var(--vf-text, #27272a);
  font-size: 12px;
  font-weight: 600;
}

@media (max-width: 700px) {
  .structure-grid {
    grid-template-columns: 1fr;
  }

  .structure-item:nth-child(odd) {
    border-right: none;
  }

  .structure-item:nth-last-child(-n + 2) {
    border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  }

  .structure-item:last-child {
    border-bottom: none;
  }
}
</style>