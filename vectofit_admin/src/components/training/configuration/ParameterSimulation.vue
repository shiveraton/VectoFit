<script setup lang="ts">
import type { ParameterSimulation } from "./trainingParameters";

const props = withDefaults(
  defineProps<{
    variant: ParameterSimulation;
    progress: number;
  }>(),
  { progress: 50 },
);

const clampedProgress = () => Math.min(100, Math.max(0, props.progress));
</script>

<template>
  <div class="simulation" aria-hidden="true">
    <div v-if="variant === 'trees'" class="tree-simulation">
      <span v-for="index in 8" :key="index" :class="['tree', { visible: index <= Math.max(1, Math.round((clampedProgress() / 100) * 8)) }]" />
    </div>

    <div v-else-if="variant === 'depth'" class="depth-simulation">
      <span v-for="index in 4" :key="index" :class="['level', { active: index <= Math.max(1, Math.ceil((clampedProgress() / 100) * 4)) }]">
        <i />
        <i />
      </span>
    </div>

    <div v-else-if="variant === 'learning'" class="curve-simulation">
      <span class="curve-path" :style="{ '--curve-progress': `${clampedProgress()}%` }"></span>
      <span class="curve-dot" :style="{ left: `${Math.max(7, clampedProgress())}%` }"></span>
    </div>

    <div v-else-if="variant === 'subsample' || variant === 'features'" class="sample-simulation">
      <span v-for="index in 12" :key="index" :class="['sample', { kept: index <= Math.max(1, Math.round((clampedProgress() / 100) * 12)) }]" />
    </div>

    <div v-else-if="variant === 'child-weight' || variant === 'regularization'" class="bar-simulation">
      <span class="bar-track">
        <span class="bar-fill" :style="{ width: `${Math.max(10, clampedProgress())}%` }"></span>
      </span>
      <span class="bar-caption"></span>
    </div>

    <div v-else-if="variant === 'split'" class="split-simulation">
      <span class="split-train" :style="{ width: `${100 - clampedProgress()}%` }"></span>
      <span class="split-test" :style="{ width: `${clampedProgress()}%` }"></span>
    </div>

    <div v-else class="seed-simulation">
      <span v-for="index in 5" :key="index" :class="['seed-box', { active: index === 3 }]">
        {{ index + 3 }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.simulation {
  height: 34px;
  margin-top: 13px;
  padding: 8px 10px;
  background: #fafafa;
  border: 1px solid var(--vf-border-light);
  border-radius: 7px;
}

.tree-simulation,
.depth-simulation,
.sample-simulation,
.seed-simulation {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 4px;
  height: 100%;
}

.tree {
  width: 8px;
  height: 8px;
  background: #e4e4e7;
  border-radius: 2px 2px 5px 5px;
}

.tree.visible {
  height: 14px;
  background: linear-gradient(180deg, #fb923c, #ef4444);
}

.depth-simulation {
  align-items: center;
  justify-content: center;
}

.level {
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: 26px;
  opacity: 0.2;
}

.level.active {
  opacity: 1;
}

.level i {
  display: block;
  height: 4px;
  background: #fb923c;
  border-radius: 3px;
}

.level i:last-child {
  width: 70%;
  align-self: flex-end;
  background: #ef4444;
}

.curve-simulation {
  position: relative;
  height: 100%;
}

.curve-path {
  position: absolute;
  inset: 7px 4% 7px;
  border-top: 2px solid #fb923c;
  border-right: 2px solid transparent;
  border-radius: 70% 50% 0 0;
  transform: skewX(-16deg);
}

.curve-dot {
  position: absolute;
  top: 50%;
  width: 8px;
  height: 8px;
  background: #ef4444;
  border-radius: 50%;
  transform: translate(-50%, -50%);
}

.sample {
  width: 8px;
  height: 8px;
  background: #e4e4e7;
  border-radius: 2px;
}

.sample.kept {
  background: #fb923c;
}

.bar-simulation {
  display: flex;
  align-items: center;
  height: 100%;
}

.bar-track {
  width: 100%;
  height: 5px;
  overflow: hidden;
  background: #e4e4e7;
  border-radius: 999px;
}

.bar-fill {
  display: block;
  height: 100%;
  background: var(--vf-gradient);
  border-radius: inherit;
  transition: width 0.2s ease;
}

.split-simulation {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: #f4f4f5;
  border-radius: 4px;
}

.split-simulation span {
  height: 100%;
}

.split-train {
  background: #fb923c;
}

.split-test {
  background: #ef4444;
}

.seed-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 18px;
  color: #a1a1aa;
  background: #f4f4f5;
  border-radius: 4px;
  font-size: 8px;
  font-weight: 700;
}

.seed-box.active {
  color: #ffffff;
  background: var(--vf-gradient);
}
</style>
