<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { CreateDatasetPayload } from "../../services/datasetService";
import type { Participant } from "../../services/participantService";

const props = defineProps<{
  isOpen: boolean;
  isSubmitting: boolean;
  form: CreateDatasetPayload;
  participants: Participant[];
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "submit"): void;
  (e: "create-participant"): void;
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const nameInputRef = ref<HTMLInputElement | null>(null);
const participantSelectRef = ref<HTMLSelectElement | null>(null);
const viewAngleSelectRef = ref<HTMLSelectElement | null>(null);

const fileError = ref("");
const formError = ref("");

const selectedFileName = computed(() => props.form.video_file?.name ?? "");

const canSubmit = computed(() => {
  return (
    !props.isSubmitting &&
    props.form.name.trim().length > 0 &&
    props.form.video_file !== null &&
    typeof props.form.participant === "number" &&
    [1, 2, 3].includes(props.form.view_angle ?? 0) &&
    !fileError.value
  );
});

watch(
  () => props.isOpen,
  (isOpen) => {
    formError.value = "";
    fileError.value = "";

    if (!isOpen) {
      props.form.video_file = null;

      if (fileInputRef.value) {
        fileInputRef.value.value = "";
      }
    }
  },
);

function closeModal() {
  if (props.isSubmitting) return;

  emit("close");
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] ?? null;

  fileError.value = "";
  formError.value = "";

  props.form.video_file = null;

  if (!file) return;

  if (!file.name.toLowerCase().endsWith(".mp4")) {
    fileError.value = "Please select an MP4 video file.";
    input.value = "";
    return;
  }

  props.form.video_file = file;
}

function handleSubmit() {
  formError.value = "";

  if (props.isSubmitting) return;

  if (!props.form.name.trim()) {
    formError.value = "Enter a dataset name.";
    nameInputRef.value?.focus();
    return;
  }

  if (!props.form.video_file || fileError.value) {
    fileError.value = fileError.value || "Select an MP4 video.";
    fileInputRef.value?.focus();
    return;
  }

  if (props.form.participant == null) {
    formError.value = "Select a participant.";
    participantSelectRef.value?.focus();
    return;
  }

  if (![1, 2, 3].includes(props.form.view_angle ?? 0)) {
    formError.value = "Select the video's view angle.";
    viewAngleSelectRef.value?.focus();
    return;
  }

  emit("submit");
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="modal-overlay"
      @click.self="closeModal"
      @keydown.esc="closeModal"
    >
      <section
        class="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dataset-modal-title"
      >
        <header class="modal-header">
          <div>
            <p class="eyebrow">DATASET MANAGEMENT</p>
            <h2 id="dataset-modal-title">Create New Dataset</h2>
            <p class="modal-description">
              Register a squat video for processing and analysis.
            </p>
          </div>

          <button
            type="button"
            class="close-btn"
            aria-label="Close dialog"
            :disabled="isSubmitting"
            @click="closeModal"
          >
            ✕
          </button>
        </header>

        <form class="modal-body" @submit.prevent="handleSubmit">
          <div v-if="formError" class="form-error" role="alert">
            {{ formError }}
          </div>

          <div class="form-group">
            <label for="dataset-name">Dataset Name <span>*</span></label>

            <input
              id="dataset-name"
              ref="nameInputRef"
              v-model="form.name"
              type="text"
              placeholder="e.g. Squat_Rep_Landmarks_v1"
              autocomplete="off"
              required
            />
          </div>

          <div class="form-group">
            <label for="dataset-desc">Description</label>

            <textarea
              id="dataset-desc"
              v-model="form.description"
              rows="3"
              placeholder="Describe the data source and recording conditions."
            />
          </div>

          <div class="form-group">
            <label for="dataset-video">Raw Exercise Video <span>*</span></label>

            <label
              for="dataset-video"
              class="file-picker"
              :class="{ 'file-picker-error': fileError }"
            >
              <span class="file-icon" aria-hidden="true">↑</span>

              <span class="file-copy">
                <strong>
                  {{ selectedFileName || "Choose an MP4 video" }}
                </strong>
                <span>
                  {{
                    selectedFileName
                      ? "Video selected"
                      : "Select a video from your device"
                  }}
                </span>
              </span>

              <span class="browse-label">Browse</span>
            </label>

            <input
              id="dataset-video"
              ref="fileInputRef"
              class="native-file-input"
              type="file"
              accept=".mp4,video/mp4"
              required
              @change="handleFileChange"
            />

            <p v-if="fileError" class="field-error" role="alert">
              {{ fileError }}
            </p>
            <p v-else class="field-hint">
              MP4 format only. The backend will validate the uploaded file.
            </p>
          </div>

          <div class="form-group">
            <label for="dataset-participant">Participant <span>*</span></label>

            <div class="participant-row">
              <select
                id="dataset-participant"
                ref="participantSelectRef"
                v-model="form.participant"
                required
              >
                <option :value="null" disabled>Select participant</option>

                <option
                  v-for="participant in participants"
                  :key="participant.id"
                  :value="participant.id"
                >
                  {{ participant.participant_code }}
                </option>
              </select>

              <button
                type="button"
                class="add-participant-button"
                title="Create participant"
                aria-label="Create participant"
                :disabled="isSubmitting"
                @click="emit('create-participant')"
              >
                +
              </button>
            </div>

            <p v-if="participants.length === 0" class="field-hint">
              No participants available. Create a participant first.
            </p>
          </div>

          <div class="form-group">
            <label for="dataset-view-angle">View Angle <span>*</span></label>

            <select
              id="dataset-view-angle"
              ref="viewAngleSelectRef"
              v-model="form.view_angle"
              required
            >
              <option :value="null" disabled>Select the recording angle</option>
              <option :value="1">Diagonal / 45°</option>
              <option :value="2">Frontal</option>
              <option :value="3">Sagittal</option>
            </select>
          </div>

          <footer class="modal-footer">
            <button
              type="button"
              class="secondary-button"
              :disabled="isSubmitting"
              @click="closeModal"
            >
              Cancel
            </button>

            <button type="submit" class="primary-button" :disabled="!canSubmit">
              <span v-if="isSubmitting" class="spinner" aria-hidden="true" />
              {{ isSubmitting ? "Creating dataset..." : "Create Dataset" }}
            </button>
          </footer>
        </form>
      </section>
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
  overflow-y: auto;
  padding: 24px 16px;
  background: rgb(24 24 27 / 48%);
  backdrop-filter: blur(5px);
}

.modal-card {
  width: min(100%, 520px);
  max-height: calc(100dvh - 48px);
  overflow-y: auto;
  background: var(--vf-surface, #fff);
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 16px;
  box-shadow: 0 24px 70px rgb(0 0 0 / 18%);
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 26px 20px;
  border-bottom: 1px solid var(--vf-border, #e4e4e7);
}

.eyebrow {
  margin: 0 0 7px;
  color: var(--vf-orange, #f97316);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.1px;
}

.modal-header h2 {
  margin: 0;
  color: var(--vf-dark, #18181b);
  font-size: 21px;
  font-weight: 750;
}

.modal-description {
  margin: 7px 0 0;
  color: var(--vf-muted, #71717a);
  font-size: 12px;
  line-height: 1.5;
}

.close-btn {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 9px;
  background: transparent;
  color: var(--vf-muted, #71717a);
  cursor: pointer;
}

.close-btn:hover:not(:disabled) {
  background: #f4f4f5;
  color: #18181b;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px 26px 26px;
}

.form-group {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 7px;
}

.form-group > label {
  color: var(--vf-text, #27272a);
  font-size: 12px;
  font-weight: 700;
}

.form-group > label span {
  color: #ea580c;
}

.form-group input[type="text"],
.form-group textarea,
.form-group select {
  box-sizing: border-box;
  width: 100%;
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 8px;
  outline: none;
  background: var(--vf-input-bg, #fafafa);
  color: var(--vf-text, #27272a);
  font: inherit;
  font-size: 13px;
  transition:
    border-color 150ms ease,
    box-shadow 150ms ease;
}

.form-group textarea {
  min-height: 86px;
  resize: vertical;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  border-color: var(--vf-orange, #f97316);
  box-shadow: 0 0 0 3px rgb(249 115 22 / 12%);
}

.file-picker {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 14px;
  border: 1px dashed var(--vf-border, #d4d4d8);
  border-radius: 10px;
  background: #fafafa;
  cursor: pointer;
  transition:
    border-color 150ms ease,
    background 150ms ease;
}

.file-picker:hover {
  border-color: var(--vf-orange, #f97316);
  background: #fff7ed;
}

.file-picker-error {
  border-color: #dc2626;
  background: #fef2f2;
}

.file-icon {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 9px;
  background: #ffedd5;
  color: #c2410c;
  font-size: 23px;
  font-weight: 700;
}

.file-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 4px;
}

.file-copy strong {
  overflow: hidden;
  color: var(--vf-text, #27272a);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-copy > span {
  color: var(--vf-muted, #71717a);
  font-size: 11px;
}

.browse-label {
  flex: 0 0 auto;
  color: #c2410c;
  font-size: 11px;
  font-weight: 700;
}

.native-file-input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  clip-path: inset(50%);
}

.native-file-input:focus-visible + .field-hint {
  outline: 2px solid var(--vf-orange, #f97316);
}

.participant-row {
  display: flex;
  align-items: stretch;
  gap: 8px;
}

.participant-row select {
  flex: 1;
  min-width: 0;
}

.add-participant-button {
  display: grid;
  width: 42px;
  flex: 0 0 42px;
  place-items: center;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #c2410c;
  font-size: 22px;
  cursor: pointer;
}

.add-participant-button:hover:not(:disabled) {
  background: #ffedd5;
}

.field-hint {
  margin: 0;
  color: var(--vf-muted, #71717a);
  font-size: 11px;
  line-height: 1.5;
}

.field-error,
.form-error {
  color: #b91c1c;
  font-size: 12px;
  line-height: 1.5;
}

.form-error {
  padding: 10px 12px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fef2f2;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--vf-border, #e4e4e7);
}

.primary-button,
.secondary-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    opacity 150ms ease,
    background 150ms ease;
}

.primary-button {
  border: none;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  color: white;
}

.secondary-button {
  border: 1px solid var(--vf-border, #e4e4e7);
  background: var(--vf-surface, #fff);
  color: var(--vf-text, #27272a);
}

.primary-button:disabled,
.secondary-button:disabled,
.close-btn:disabled,
.add-participant-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgb(255 255 255 / 45%);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 700ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 480px) {
  .modal-overlay {
    align-items: flex-start;
    padding: 12px;
  }

  .modal-card {
    max-height: calc(100dvh - 24px);
  }

  .modal-header,
  .modal-body {
    padding-right: 18px;
    padding-left: 18px;
  }

  .modal-footer {
    flex-direction: column-reverse;
  }

  .modal-footer button {
    width: 100%;
  }
}
</style>
