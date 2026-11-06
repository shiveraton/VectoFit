<script setup lang="ts">
import type { ModelRegistryRecord } from "../../services/modelService";

defineProps<{
  models: ModelRegistryRecord[];
  selectedModelId: number | null;
}>();

defineEmits<{
  (event: "select", id: number): void;
}>();

const accuracy = (model: ModelRegistryRecord) => {
  const value = model.metrics?.accuracy;

  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "—";
};

const formatDate = (value: string) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(new Date(value));
</script>

<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th scope="col">VERSION</th>
          <th scope="col">FPPA TARGET</th>
          <th scope="col">HELD-OUT ACCURACY</th>
          <th scope="col">TRAINING JOB</th>
          <th scope="col">STATUS</th>
          <th scope="col">CREATED</th>
        </tr>
      </thead>

      <tbody>
        <tr
          v-for="model in models"
          :key="model.id"
          :class="{
            selected: model.id === selectedModelId,
          }"
          @click="$emit('select', model.id)"
        >
          <td class="version-cell">
            <button type="button" class="version-select" :aria-pressed="model.id === selectedModelId" :aria-label="`Inspect ${model.name}, version ${model.version}`" @click.stop="$emit('select', model.id)">v{{ model.version }}</button>
            <span>{{ model.name }}</span>
          </td>

          <td>
            Good / bad knee alignment
          </td>

          <td class="numeric">
            {{ accuracy(model) }}
          </td>

          <td class="numeric">#{{ model.training_job }}</td>

          <td>
            <span class="status" :class="{ active: model.is_active }">
              {{ model.is_active ? "ACTIVE" : "REGISTERED" }}
            </span>
          </td>

          <td>
            {{ formatDate(model.created_at) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
}

th {
  padding: 12px 18px;
  background: #fafafa;
  color: var(--vf-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-align: left;
}

td {
  padding: 14px 18px;
  border-top: 1px solid var(--vf-border-light);
  color: var(--vf-dark);
  font-size: 13px;
}

tbody tr {
  cursor: pointer;
  transition: background 0.15s ease;
}

tbody tr:hover,
tbody tr.selected {
  background: rgba(249, 115, 22, 0.045);
}

.version-cell strong {
  display: block;
  font-size: 12px;
}

.version-cell span {
  display: block;
  margin-top: 2px;
  color: var(--vf-muted);
  font-size: 12px;
}

.numeric {
  font-variant-numeric: tabular-nums;
}

.status {
  display: inline-flex;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f4f4f5;
  color: #71717a;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.status.active {
  background: #fff7ed;
  color: var(--vf-orange-dark);
}
.version-select { display: inline-flex; min-height: 32px; align-items: center; padding: 2px 8px; margin-left: -8px; border: 0; border-radius: 4px; background: transparent; color: var(--vf-orange); font-weight: 600; cursor: pointer; }
.version-select[aria-pressed="true"] { background: #ffedd5; }
tbody tr.selected { box-shadow: inset 3px 0 var(--vf-orange); }
</style>
