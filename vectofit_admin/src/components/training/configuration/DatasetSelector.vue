<script setup lang="ts">
import { computed } from "vue";
import type { Dataset, ViewAngle } from "../../../services/datasetService";

type DatasetId = number;

const props = defineProps<{
  availableDatasets: Dataset[];
  filteredDatasets: Dataset[];
  selectedDatasetIds: DatasetId[];
  selectedDatasets: Dataset[];
  selectedViewAngle: ViewAngle | null;
}>();

const emit = defineEmits<{
  (event: "toggle-dataset", id: DatasetId): void;
}>();

const selectedCount = computed(() => props.selectedDatasets.length);

const selectedSamples = computed(() =>
  props.selectedDatasets.reduce(
    (total, dataset) => total + Number(dataset.sample_count || 0),
    0,
  ),
);

const selectedLabelledSamples = computed(() =>
  props.selectedDatasets.reduce(
    (total, dataset) => total + Number(dataset.labelled_sample_count || 0),
    0,
  ),
);

const formatNumber = (value: number) => value.toLocaleString("en-US");
</script>

<template>
  <section class="configuration-section wide-section">
    <div class="configuration-label">
      <div>
        <strong>Datasets</strong>
        <span
          >Select prepared datasets that belong to the same camera view.</span
        >
      </div>
    </div>

    <div class="dataset-selection">
      <button
        v-for="dataset in filteredDatasets"
        :key="dataset.id"
        type="button"
        :class="[
          'dataset-option',
          { selected: selectedDatasetIds.includes(dataset.id) },
        ]"
        @click="emit('toggle-dataset', dataset.id)"
      >
        <span class="dataset-check" aria-hidden="true">
          {{ selectedDatasetIds.includes(dataset.id) ? "✓" : "" }}
        </span>

        <span class="dataset-main">
          <span class="dataset-title-row">
            <strong>{{ dataset.name }}</strong>
            <small>#{{ dataset.id }}</small>
          </span>

          <span class="dataset-meta">
            <span v-if="dataset.exercise_type">{{
              dataset.exercise_type
            }}</span>
            <span>{{ dataset.labelled_sample_count ?? 0 }} labelled</span>
            <span>{{ dataset.sample_count ?? 0 }} samples</span>
          </span>
        </span>
      </button>

      <div v-if="!filteredDatasets.length" class="inline-empty">
        <strong>
          {{
            selectedViewAngle
              ? "No usable datasets are available for this view."
              : "Select a camera view to display compatible datasets."
          }}
        </strong>
      </div>
    </div>

    <div class="selection-summary">
      <span>
        <strong>{{ selectedCount }}</strong>
        dataset{{ selectedCount === 1 ? "" : "s" }} selected
      </span>
      <span v-if="selectedCount">
        {{ formatNumber(selectedLabelledSamples) }} labelled ·
        {{ formatNumber(selectedSamples) }} samples
      </span>
      <span v-else>Choose at least one dataset to train.</span>
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
  font-weight: 700;
}

.configuration-label div > span {
  margin-top: 4px;
  color: var(--vf-light-muted);
  font-size: 10px;
  line-height: 1.5;
}

.dataset-selection {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.dataset-option {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 13px;
  text-align: left;
  background: #ffffff;
  border: 1px solid var(--vf-border);
  border-radius: 9px;
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    background 0.16s ease,
    box-shadow 0.16s ease;
}

.dataset-option:hover {
  background: #fffaf6;
  border-color: #fdba74;
}

.dataset-option.selected {
  background: #fffaf6;
  border-color: #fb923c;
  box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.08);
}

.dataset-check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  margin-top: 1px;
  color: #ffffff;
  background: #ffffff;
  border: 1.5px solid #d4d4d8;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 800;
}

.selected .dataset-check {
  background: var(--vf-gradient);
  border-color: transparent;
}

.dataset-main {
  min-width: 0;
  flex: 1;
}

.dataset-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.dataset-title-row strong {
  min-width: 0;
  overflow: hidden;
  color: var(--vf-text);
  font-size: 11px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dataset-title-row small {
  color: var(--vf-light-muted);
  font-size: 9px;
  font-weight: 600;
}

.dataset-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 9px;
  margin-top: 7px;
  color: var(--vf-muted);
  font-size: 9px;
}

.dataset-meta span + span::before {
  content: "·";
  margin-right: 9px;
  color: #d4d4d8;
}

.inline-empty {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 18px;
  color: var(--vf-muted);
  background: #fcfcfc;
  border: 1px dashed var(--vf-border);
  border-radius: 8px;
  text-align: center;
  font-size: 10px;
}

.inline-empty strong {
  color: var(--vf-text);
  font-size: 11px;
}

.selection-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 11px;
  color: var(--vf-light-muted);
  font-size: 9px;
}

.selection-summary strong {
  color: var(--vf-text);
}

@media (max-width: 800px) {
  .dataset-selection {
    grid-template-columns: 1fr;
  }

  .selection-summary {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
