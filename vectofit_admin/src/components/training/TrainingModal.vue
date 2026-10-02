<script setup>
import { ref, computed } from "vue";
import axios from "axios";

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  datasetIds: {
    type: [Array, Number, String],
    required: true,
  },
});

const emit = defineEmits(["close", "job-started"]);

const formattedDatasetIds = computed(() => {
  if (!props.datasetIds) return [];
  if (Array.isArray(props.datasetIds)) {
    return props.datasetIds.map(Number).filter((id) => !isNan(id) && id > 0);
  }
  const num = Number(props.datasetIds);
  return isNan(num) || num <= 0 ? [] : [num];
});

const availableFeatures = [
  { key: "rom", label: "Range of Motion (ROM)" },
  { key: "velocity", label: "Velocity (Mean & Peak)" },
  { key: "asymmetry", label: "Bilateral Asymmetry" },
];

const isSubmitting = ref(false);
const errorMessage = ref("");

const form = ref({
  feature_selection: ["rom", "velocity", "asymmetry"],
  test_size: 0.3,
  random_seed: 42,
  hyperparameters: {
    n_estimators: 100,
    max_depth: 4,
  },
});

const isValid = computed(() => {
  return (
    form.value.feature_selection.length > 0 &&
    form.value.test_size >= 0.1 &&
    form.value.test_size <= 0.5 &&
    (formattedDatasetIds.value.length > 0 || props.isOpen)
  );
});

function close() {
  errorMessage.value = "";
  emit("close");
}

async function handleSubmit() {
  if (!isValid.value) return;
  isSubmitting.value = true;
  errorMessage.value = "";

  const payload = {
    dataset_ids: formattedDatasetIds.value,
    feature_selection: form.value.feature_selection,
    test_size: form.value.test_size,
    random_seed: form.value.random_seed,
    hyperparameters: form.value.hyperparameters,
  };

  try {
    const { data } = await axios.post("/api/v1/training/start/", payload);
    emit("job-started", data);
    close();
  } catch (err) {
    if (err.response && err.response.data) {
      const fieldErrors = err.response.data;
      errorMessage.value =
        typeof fieldErrors === "object"
          ? Object.entries(fieldErrors)
              .map(([k, v]) => `${k}: ${v}`)
              .join(" | ")
          : "Failed to initiate training job.";
    } else {
      errorMessage.value =
        "Network error. Could not connect to training service.";
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="modal-overlay" @click.self="close">
      <div class="modal-card">
        <header class="modal-header">
          <h3>Configure Training Run</h3>
          <button class="btn-close" @click="close">&times;</button>
        </header>

        <form @submit.prevent="handleSubmit" class="modal-body">
          <div class="form-group">
            <label>Selected Dataset IDs</label>
            <div class="dataset-pills">
              <span v-for="id in formattedDatasetIds" :key="id" class="pill">
                Dataset #{{ id }}
              </span>
            </div>
          </div>

          <div class="form-group">
            <label>Feature Selection</label>
            <div class="checkbox-group">
              <label v-for="feature in availableFeatures" :key="feature.key">
                <input
                  type="checkbox"
                  :value="feature.key"
                  v-model="form.feature_selection"
                />
                {{ feature.label }}
              </label>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label
                >Test Split ({{ (form.test_size * 100).toFixed(0) }}%)</label
              >
              <input
                type="range"
                min="0.1"
                max="0.5"
                step="0.05"
                v-model.number="form.test_size"
              />
            </div>
            <div class="form-group">
              <label>Random Seed</label>
              <input type="number" v-model.number="form.random_seed" min="0" />
            </div>
          </div>

          <div class="form-section">
            <h4>XGBoost Hyperparameters</h4>
            <div class="form-row">
              <div class="form-group">
                <label>Estimators (Trees)</label>
                <input
                  type="number"
                  v-model.number="form.hyperparameters.n_estimators"
                  min="1"
                  max="500"
                />
              </div>
              <div class="form-group">
                <label>Max Depth</label>
                <input
                  type="number"
                  v-model.number="form.hyperparameters.max_depth"
                  min="1"
                  max="15"
                />
              </div>
            </div>
          </div>

          <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>

          <footer class="modal-footer">
            <button
              type="button"
              class="btn-secondary"
              @click="close"
              :disabled="isSubmitting"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="isSubmitting || !isValid"
            >
              {{ isSubmitting ? "Launching Job..." : "Start Training" }}
            </button>
          </footer>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(24, 24, 27, 0.4);
  backdrop-filter: blur(4px);
}

.modal-card {
  width: 100%;
  max-width: 480px;
  background: var(--vf-surface, #ffffff);
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  color: var(--vf-text, #27272a);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--vf-dark, #18181b);
}

.btn-close,
.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  line-height: 1;
  color: var(--vf-muted, #71717a);
  cursor: pointer;
  transition: color 0.15s ease;
}

.btn-close:hover,
.close-btn:hover {
  color: var(--vf-dark, #18181b);
}

.modal-body {
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.form-group label {
  font-size: 11px;
  font-weight: 700;
  color: var(--vf-text, #27272a);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--vf-border-light, #f1f1f2);
}

.form-section h4 {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--vf-dark, #18181b);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.dataset-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pill {
  background: rgba(249, 115, 22, 0.1);
  border: 1px solid rgba(249, 115, 22, 0.25);
  color: var(--vf-orange, #f97316);
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
}

.checkbox-group {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  text-transform: none;
  color: var(--vf-text, #27272a);
}

input[type="checkbox"] {
  accent-color: var(--vf-orange, #f97316);
  cursor: pointer;
}

input[type="number"],
input[type="range"] {
  padding: 9px 12px;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 7px;
  font-family: inherit;
  font-size: 13px;
  background: #fafafa;
  color: var(--vf-text, #27272a);
  outline: none;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}

input[type="number"]:focus {
  border-color: var(--vf-orange, #f97316);
  background: #ffffff;
}

input[type="range"] {
  accent-color: var(--vf-orange, #f97316);
  padding: 0;
  height: 6px;
  background: #e4e4e7;
  cursor: pointer;
}

.error-banner {
  color: #ef4444;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 8px 12px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 500;
  margin: 0;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

.primary-button,
.btn-primary,
.secondary-button,
.btn-secondary {
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition:
    opacity 0.15s ease,
    background 0.15s ease;
}

.primary-button,
.btn-primary {
  color: #ffffff;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  border: none;
}

.primary-button:disabled,
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-button,
.btn-secondary {
  background: #f4f4f5;
  border: 1px solid var(--vf-border, #e4e4e7);
  color: var(--vf-text, #27272a);
}

.secondary-button:hover:not(:disabled),
.btn-secondary:hover:not(:disabled) {
  background: #e4e4e7;
}
</style>
