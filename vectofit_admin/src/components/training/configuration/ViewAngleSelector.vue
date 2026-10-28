<script setup lang="ts">
type ViewAngle = "diagonal" | "frontal" | "sagittal";

const props = defineProps<{
  selectedViewAngle: ViewAngle | null;
}>();

const emit = defineEmits<{
  (event: "select-view-angle", angle: ViewAngle): void;
}>();

const viewAngles: Array<{
  id: ViewAngle;
  label: string;
  subtitle: string;
  description: string;
}> = [
  {
    id: "diagonal",
    label: "Diagonal",
    subtitle: "45° view",
    description: "Useful for combined posture and movement assessment.",
  },
  {
    id: "frontal",
    label: "Frontal",
    subtitle: "Front-facing view",
    description: "Useful for bilateral alignment and symmetry analysis.",
  },
  {
    id: "sagittal",
    label: "Sagittal",
    subtitle: "Side view",
    description: "Useful for depth, trunk position, and forward-back motion.",
  },
];
</script>

<template>
  <section class="configuration-section wide-section">
    <div class="configuration-label">
      <div>
        <strong>View Angle</strong>
        <span>Train one view-specific model at a time.</span>
      </div>
    </div>

    <div class="view-options">
      <button
        v-for="view in viewAngles"
        :key="view.id"
        type="button"
        :class="[
          'view-option',
          { selected: props.selectedViewAngle === view.id },
        ]"
        @click="emit('select-view-angle', view.id)"
      >
        <span class="view-icon" aria-hidden="true">
          {{
            view.id === "diagonal" ? "45" : view.id === "frontal" ? "F" : "S"
          }}
        </span>

        <span class="view-copy">
          <strong>{{ view.label }}</strong>
          <small>{{ view.subtitle }}</small>
          <span>{{ view.description }}</span>
        </span>

        <span class="view-indicator" aria-hidden="true"></span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.configuration-section {
  padding: 24px 22px;
  border-bottom: 1px solid var(--vf-border-light);
}

.wide-section {
  grid-column: 1 / -1;
}

.configuration-label {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  margin-bottom: 15px;
}

.configuration-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 27px;
  height: 27px;
  flex-shrink: 0;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border: 1px solid #fed7aa;
  border-radius: 7px;
  font-size: 9px;
  font-weight: 800;
}

.configuration-label strong,
.configuration-label span {
  display: block;
}

.configuration-label strong {
  color: var(--vf-text);
  font-size: 12px;
}

.configuration-label div > span {
  margin-top: 4px;
  color: var(--vf-light-muted);
  font-size: 10px;
}

.view-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.view-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  padding: 13px;
  text-align: left;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.view-option:hover {
  background: #fffaf6;
  border-color: #fdba74;
}

.view-option.selected {
  background: #fffaf6;
  border-color: #fb923c;
  box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.08);
}

.view-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  color: var(--vf-orange-dark);
  background: var(--vf-orange-soft);
  border-radius: 7px;
  font-size: 9px;
  font-weight: 800;
}

.view-copy {
  min-width: 0;
  flex: 1;
}

.view-copy strong,
.view-copy small,
.view-copy > span {
  display: block;
}

.view-copy strong {
  color: var(--vf-text);
  font-size: 11px;
  font-weight: 700;
}

.view-copy small {
  margin-top: 2px;
  color: var(--vf-orange-dark);
  font-size: 9px;
  font-weight: 700;
}

.view-copy > span {
  margin-top: 6px;
  color: var(--vf-light-muted);
  font-size: 9px;
  line-height: 1.45;
}

.view-indicator {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
  margin-top: 2px;
  border: 1.5px solid #d4d4d8;
  border-radius: 50%;
}

.selected .view-indicator {
  border: 3px solid #fb923c;
  box-shadow: inset 0 0 0 1px #ffffff;
}

@media (max-width: 800px) {
  .view-options {
    grid-template-columns: 1fr;
  }
}
</style>
