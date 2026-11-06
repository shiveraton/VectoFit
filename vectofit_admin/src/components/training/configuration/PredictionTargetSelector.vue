<script setup lang="ts">
import type { PredictionTarget } from "../../../services/trainingService";
const props = defineProps<{ modelValue: PredictionTarget }>();
const emit = defineEmits<{ (event: "update:modelValue", value: PredictionTarget): void }>();
</script>
<template>
  <section class="configuration-section wide-section">
    <div class="configuration-label"><div><strong>Learning Target</strong><span>Choose what the classifier should learn from each repetition.</span></div></div>
    <div class="target-options">
      <button type="button" class="target-option" :class="{ selected: props.modelValue === 'binary_form' }" @click="emit('update:modelValue', 'binary_form')">
        <strong>Form quality</strong><span>GOOD vs BAD — uses labelled repetitions, including source labels and human corrections.</span><small>Recommended baseline</small>
      </button>
      <button type="button" class="target-option" :class="{ selected: props.modelValue === 'error_type' }" @click="emit('update:modelValue', 'error_type')">
        <strong>Error type</strong><span>Correct form vs specific error_label categories. Incorrect repetitions without an error label are excluded.</span><small>Requires specific error labels</small>
      </button>
      <button type="button" class="target-option" :class="{ selected: props.modelValue === 'knee_alignment' }" @click="emit('update:modelValue', 'knee_alignment')">
        <strong>Frontal-plane knee alignment</strong><span>Good vs bad final knee-annotation targets. Requires completed human knee annotations with agreement across annotators.</span><small>Frontal / diagonal pilot target</small>
      </button>
    </div>
  </section>
</template>
<style scoped>
.configuration-section { padding: 24px 22px; border-bottom: 1px solid var(--vf-border-light); }
.wide-section { grid-column: 1 / -1; }
.configuration-label { display: flex; align-items: flex-start; margin-bottom: 15px; }
.configuration-label strong, .configuration-label span { display: block; }
.configuration-label strong { color: var(--vf-text); font-size: 12px; }
.configuration-label div > span { margin-top: 4px; color: var(--vf-light-muted); font-size: 10px; line-height: 1.5; }
.target-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.target-option { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; min-width: 0; padding: 14px; border: 1px solid var(--vf-border); border-radius: 9px; background: #fff; text-align: left; cursor: pointer; }
.target-option.selected { border-color: #fb923c; background: #fffaf6; box-shadow: 0 0 0 2px rgba(249, 115, 22, .08); }
.target-option strong { color: var(--vf-text); font-size: 12px; }
.target-option span { color: var(--vf-muted); font-size: 10px; line-height: 1.5; }
.target-option small { color: var(--vf-orange-dark); font-size: 9px; font-weight: 700; }
@media (max-width: 800px) { .target-options { grid-template-columns: 1fr; } }
</style>
