<script setup lang="ts">
import type { CreateDatasetPayload } from "../../services/datasetService";
import { ref, watch } from "vue";

const props = defineProps<{
  isOpen: boolean;
  isSubmitting: boolean;
  form: CreateDatasetPayload;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "submit"): void;
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const fileError = ref("");

watch(
  () => props.isOpen,
  (newVal) => {
    if (!newVal) {
      fileError.value = "";
      if (fileInputRef.value) {
        fileInputRef.value.value = "";
      }
    }
  },
);

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  fileError.value = "";

  if (!file) {
    props.form.video_file = null;
    return;
  }

  if (file.type !== "video/mp4") {
    fileError.value = "Only MP4 videos are supported.";
    props.form.video_file = null;
    return;
  }

  props.form.video_file = file;
};
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Create New Dataset</h3>
          <button type="button" class="close-btn" @click="$emit('close')">
            ✕
          </button>
        </div>

        <form @submit.prevent="$emit('submit')" class="modal-body">
          <div class="form-group">
            <label for="dataset-name">Dataset Name</label>
            <input
              id="dataset-name"
              v-model="form.name"
              type="text"
              placeholder="e.g. Squat_Rep_Landmarks_v1"
              required
            />
          </div>

          <div class="form-group">
            <label for="dataset-desc">Description</label>
            <textarea
              id="dataset-desc"
              v-model="form.description"
              rows="3"
              placeholder="Brief description of data source and conditions..."
            ></textarea>
          </div>

          <div class="form-group">
            <label for="dataset-video">Raw Exercise Video</label>
            <input
              id="dataset-video"
              type="file"
              accept="video/mp4"
              @change="handleFileChange"
              required
            />
            <span v-if="fileError" class="field-error">{{ fileError }}</span>
          </div>

          <div class="modal-footer">
            <button
              type="button"
              class="secondary-button"
              @click="$emit('close')"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="primary-button"
              :disabled="isSubmitting || !form.name"
            >
              {{ isSubmitting ? "Creating..." : "Create Dataset" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 999;
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

.close-btn {
  background: none;
  border: none;
  font-size: 16px;
  color: var(--vf-muted, #71717a);
  cursor: pointer;
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
}

.form-group label {
  font-size: 11px;
  font-weight: 700;
  color: var(--vf-text, #27272a);
}

.form-group input,
.form-group textarea {
  padding: 10px 12px;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 7px;
  font-family: inherit;
  font-size: 13px;
  background: #fafafa;
  color: var(--vf-text, #27272a);
  outline: none;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: var(--vf-orange, #f97316);
  background: #ffffff;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

.primary-button,
.secondary-button {
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.primary-button {
  color: #ffffff;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  border: none;
}

.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-button {
  background: #f4f4f5;
  border: 1px solid var(--vf-border, #e4e4e7);
  color: var(--vf-text, #27272a);
}
</style>
