<template>
  <div class="dataset-card">
    <div class="dataset-info">
      <div class="dataset-name">
        <strong>{{ dataset.name }}</strong>
      </div>
      <div class="dataset-meta">
        <span v-if="dataset.exercise_type">{{ exerciseTypeLabel }}</span>
        <span class="dataset-status" :class="statusClass">
          {{ statusLabel }}
        </span>
      </div>
    </div>
    <div class="dataset-actions">
      <button class="action-button" @click="annotate" :disabled="isAnnotating">
        {{ isAnnotating ? "Annotating..." : "Annotate" }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

interface DatasetProps {
  dataset: {
    id: number;
    name: string;
    exercise_type?: string;
    status: string;
  };
}

const props = defineProps<DatasetProps>();

const router = useRouter();

const exerciseTypeLabel = computed(() => {
  const exerciseType = props.dataset.exercise_type;
  if (!exerciseType) return "";

  const map: Record<string, string> = {
    bodyweight_squat: "Bodyweight Squat",
    goblet_squat: "Goblet Squat",
  };
  return map[exerciseType] || exerciseType;
});

const statusClass = computed(() => {
  const map: any = {
    PENDING: "status-pending",
    READY: "status-ready",
    PROCESSING: "status-processing",
    FAILED: "status-failed",
  };
  return map[props.dataset.status] || "";
});

const statusLabel = computed(() => {
  const map: any = {
    PENDING: "Pending",
    READY: "Ready",
    PROCESSING: "Processing",
    FAILED: "Failed",
  };
  return map[props.dataset.status] || props.dataset.status;
});

const isAnnotating = ref(false);

function annotate() {
  isAnnotating.value = true;
  router.push(`/annotator/datasets/${props.dataset.id}/annotate`);
}
</script>

<style scoped>
.dataset-card {
  background: #ffffff;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  padding: 20px;
  text-align: left;
  transition: transform 0.2s ease;
  cursor: pointer;
}

.dataset-card:hover {
  transform: translateY(-2px);
}

.dataset-info {
  margin-bottom: 12px;
}

.dataset-name {
  font-size: 16px;
  font-weight: 600;
  color: #172033;
  margin-bottom: 4px;
}

.dataset-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #8a96a8;
  font-size: 12px;
}

.dataset-status {
  padding: 3px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
}

.status-pending {
  color: #a16207;
  background: #fefce8;
}

.status-ready {
  color: #15803d;
  background: #f0fdf4;
}

.status-processing {
  color: #c2410c;
  background: #fff7ed;
}

.status-failed {
  color: #dc2626;
  background: #fef2f2;
}

.dataset-actions {
  margin-top: 12px;
  text-align: right;
}

.action-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 7px 11px;
  color: #ffffff;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  border: 1px solid transparent;
  border-radius: 6px;
  font-family: inherit;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    opacity 0.15s ease;
}

.action-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(239, 68, 68, 0.18);
}

.action-button:active {
  transform: translateY(0);
}
</style>
