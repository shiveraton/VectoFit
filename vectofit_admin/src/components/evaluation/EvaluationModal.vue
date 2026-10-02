<script setup lang="ts">
import { ref, watch } from "vue";

interface Props {
  isOpen: boolean;
  datasetIds?: string[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "evaluation-started", payload: { evaluation_id: string }): void;
}>();

const selectedModel = ref("model-v2-4");
const selectedDataset = ref("");
const batchSize = ref(32);
const confidenceThreshold = ref(0.85);
const isSubmitting = ref(false);

watch(
  () => props.datasetIds,
  (newVal) => {
    if (newVal && newVal.length > 0) {
      selectedDataset.value = newVal[0];
    } else {
      selectedDataset.value = "ds-squat-benchmark-2026";
    }
  },
  { immediate: true },
);

const handleClose = () => {
  emit("close");
};

const handleSubmit = async () => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;

  try {
    await new Promise((resolve) => setTimeout(resolve, 600));
    const generatedId = `EVAL-JOB-${Math.floor(1000 + Math.random() * 9000)}`;
    emit("evaluation-started", { evaluation_id: generatedId });
    handleClose();
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="isOpen" class="modal-backdrop" @click.self="handleClose">
        <div class="modal-card">
          <header class="modal-header">
            <div class="modal-title-group">
              <span class="modal-badge">EVALUATION JOB</span>
              <h2>Launch New Evaluation</h2>
            </div>
            <button
              class="close-btn"
              @click="handleClose"
              aria-label="Close modal"
            >
              ✕
            </button>
          </header>

          <div class="modal-body">
            <div class="form-group">
              <label class="form-label">Target Model Checkpoint</label>
              <select v-model="selectedModel" class="form-select">
                <option value="model-v2-4">
                  SquatVectorNet-v2.4 (ResNet3D Pose)
                </option>
                <option value="model-v2-3">
                  SquatVectorNet-v2.3 (MediaPipe Custom)
                </option>
                <option value="model-v1-0">
                  BaselineKinematics-v1 (Linear)
                </option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Reference Validation Dataset</label>
              <select v-model="selectedDataset" class="form-select">
                <option value="ds-squat-benchmark-2026">
                  ds-squat-benchmark-2026 (1,240 frames)
                </option>
                <option value="ds-valgus-testset-v2">
                  ds-valgus-testset-v2 (850 frames)
                </option>
                <option value="ds-kinematic-gold-standard">
                  ds-kinematic-gold-standard (2,100 frames)
                </option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Inference Batch Size</label>
                <input
                  v-model.number="batchSize"
                  type="number"
                  min="1"
                  max="128"
                  class="form-input"
                />
              </div>

              <div class="form-group">
                <label class="form-label">Keypoint Threshold</label>
                <input
                  v-model.number="confidenceThreshold"
                  type="number"
                  step="0.05"
                  min="0.5"
                  max="0.99"
                  class="form-input"
                />
              </div>
            </div>

            <div class="info-box">
              <span class="info-icon">ℹ</span>
              <p class="info-text">
                Executing this run computes joint angle matrices and vector
                similarity scores against the benchmark ground truth.
              </p>
            </div>
          </div>

          <footer class="modal-footer">
            <button
              class="button secondary"
              :disabled="isSubmitting"
              @click="handleClose"
            >
              Cancel
            </button>
            <button
              class="button primary"
              :disabled="isSubmitting || !selectedDataset || !selectedModel"
              @click="handleSubmit"
            >
              <span v-if="isSubmitting" class="spinner"></span>
              <span v-else>Start Evaluation Job</span>
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(6px);
  padding: 20px;
}

.modal-card {
  width: 100%;
  max-width: 520px;
  background: var(--vf-surface, #1e293b);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.1));
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
}

.modal-badge {
  font-family: monospace;
  font-size: 10px;
  font-weight: 700;
  color: var(--vf-orange, #f97316);
  letter-spacing: 0.1em;
}

.modal-title-group h2 {
  margin: 4px 0 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--vf-dark, #f8fafc);
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--vf-muted, #94a3b8);
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.08);
}

.modal-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.form-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--vf-muted, #94a3b8);
}

.form-select,
.form-input {
  width: 100%;
  padding: 10px 14px;
  background: var(--vf-background, #0f172a);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  color: var(--vf-dark, #f8fafc);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s ease;
}

.form-select:focus,
.form-input:focus {
  border-color: var(--vf-orange, #f97316);
}

.info-box {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: rgba(249, 115, 22, 0.06);
  border: 1px solid rgba(249, 115, 22, 0.18);
  border-radius: 8px;
}

.info-icon {
  color: var(--vf-orange, #f97316);
  font-weight: 700;
  font-size: 14px;
}

.info-text {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: var(--vf-light-muted, #94a3b8);
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 18px 24px;
  border-top: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
  background: rgba(0, 0, 0, 0.1);
}

.button {
  padding: 9px 18px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.button.secondary {
  background: rgba(255, 255, 255, 0.06);
  color: var(--vf-dark, #f8fafc);
  border: 1px solid var(--vf-border-light, rgba(255, 255, 255, 0.08));
}

.button.secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.12);
}

.button.primary {
  background: var(--vf-orange, #f97316);
  color: #ffffff;
}

.button.primary:hover:not(:disabled) {
  opacity: 0.9;
}

.button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
