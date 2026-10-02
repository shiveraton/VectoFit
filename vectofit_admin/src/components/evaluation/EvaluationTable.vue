<script setup lang="ts">
import type { EvaluationRecord } from "../../hooks/useEvaluation";

defineProps<{
  evaluations: EvaluationRecord[];
}>();

const emit = defineEmits<{
  (e: "inspect", evaluation: EvaluationRecord): void;
  (e: "delete", id: string): void;
}>();

const getStatusClass = (status: EvaluationRecord["status"]) => {
  switch (status) {
    case "COMPLETED":
      return "badge-completed";
    case "RUNNING":
      return "badge-running";
    case "FAILED":
      return "badge-failed";
    case "PENDING":
      return "badge-pending";
    default:
      return "";
  }
};

const getScoreColor = (score: number) => {
  if (score >= 90) return "score-high";
  if (score >= 75) return "score-mid";
  return "score-low";
};
</script>

<template>
  <div class="table-container">
    <table class="evaluation-table">
      <thead>
        <tr>
          <th>EVAL ID</th>
          <th>MODEL</th>
          <th>DATASET</th>
          <th>VECTOR SCORE</th>
          <th>STATUS</th>
          <th>CREATED</th>
          <th>DURATION</th>
          <th class="text-right">ACTIONS</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in evaluations" :key="item.id" class="table-row">
          <td class="font-mono eval-id">{{ item.id }}</td>
          <td class="font-medium text-main">{{ item.modelName }}</td>
          <td class="text-muted">{{ item.datasetName }}</td>
          <td>
            <div class="score-wrapper" v-if="item.status === 'COMPLETED'">
              <span class="score-value" :class="getScoreColor(item.score)">
                {{ item.score.toFixed(1) }}%
              </span>
              <div class="score-bar-bg">
                <div
                  class="score-bar-fill"
                  :class="getScoreColor(item.score)"
                  :style="{ width: `${item.score}%` }"
                ></div>
              </div>
            </div>
            <span v-else class="text-muted">--</span>
          </td>
          <td>
            <span class="status-badge" :class="getStatusClass(item.status)">
              <span class="badge-dot"></span>
              {{ item.status }}
            </span>
          </td>
          <td class="text-muted text-xs">{{ item.createdAt }}</td>
          <td class="text-muted text-xs">{{ item.duration }}</td>
          <td class="text-right">
            <div class="actions-group">
              <button
                class="action-button secondary"
                @click="emit('inspect', item)"
                title="Inspect Evaluation"
              >
                Inspect
              </button>
              <button
                class="action-button danger"
                @click="emit('delete', item.id)"
                title="Delete Record"
              >
                ✕
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-container {
  width: 100%;
  overflow-x: auto;
}

.evaluation-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}

.evaluation-table th {
  padding: 14px 20px;
  color: var(--vf-muted, #94a3b8);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
}

.table-row {
  border-bottom: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.05));
  transition: background 0.15s ease;
}

.table-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.evaluation-table td {
  padding: 14px 20px;
  vertical-align: middle;
}

.eval-id {
  color: var(--vf-orange, #f97316);
  font-weight: 600;
  font-size: 12px;
}

.text-main {
  color: var(--vf-dark, #f8fafc);
}

.text-muted {
  color: var(--vf-light-muted, #94a3b8);
}

.text-xs {
  font-size: 11px;
}

.text-right {
  text-align: right;
}

.score-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 140px;
}

.score-value {
  font-weight: 700;
  font-size: 12px;
  min-width: 42px;
}

.score-bar-bg {
  flex: 1;
  height: 5px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.score-high {
  color: #4ade80;
  background-color: #4ade80;
}

.score-mid {
  color: #fbbf24;
  background-color: #fbbf24;
}

.score-low {
  color: #f87171;
  background-color: #f87171;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.badge-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.badge-completed {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.12);
  border: 1px solid rgba(74, 222, 128, 0.25);
}

.badge-running {
  color: var(--vf-orange, #f97316);
  background: rgba(249, 115, 22, 0.12);
  border: 1px solid rgba(249, 115, 22, 0.25);
}

.badge-pending {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.12);
  border: 1px solid rgba(251, 191, 36, 0.25);
}

.badge-failed {
  color: #f87171;
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.25);
}

.actions-group {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.action-button {
  border: none;
  border-radius: 6px;
  padding: 5px 12px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-button.secondary {
  background: rgba(255, 255, 255, 0.06);
  color: var(--vf-dark, #f8fafc);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
}

.action-button.secondary:hover {
  background: rgba(255, 255, 255, 0.12);
}

.action-button.danger {
  background: rgba(248, 113, 113, 0.1);
  color: #f87171;
  padding: 5px 8px;
}

.action-button.danger:hover {
  background: rgba(248, 113, 113, 0.25);
}
</style>
