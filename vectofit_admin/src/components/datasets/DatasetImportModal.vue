<script setup lang="ts">
import { computed, ref, watch } from "vue";

import {
  datasetService,
  type DatasetImportPreview,
} from "../../services/datasetService";

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "imported", datasetName: string, videoCount: number): void;
}>();

const zipFile = ref<File | null>(null);
const preview = ref<DatasetImportPreview | null>(null);

const name = ref("VectoFit Bodyweight Squat v1");
const description = ref(
  "Labelled bodyweight squat recordings across diagonal, frontal, and sagittal views.",
);
const exerciseType = ref("bodyweight_squat");
const purpose = ref("training");
const primaryTarget = ref("squat_quality");
const secondaryTarget = ref("biomechanical_errors");

const isPreviewing = ref(false);
const isImporting = ref(false);
const errorMessage = ref("");

const canImport = computed(() => {
  return (
    Boolean(preview.value?.upload_token) &&
    preview.value?.errors.length === 0 &&
    name.value.trim().length > 0 &&
    !isImporting.value
  );
});

const reset = () => {
  zipFile.value = null;
  preview.value = null;
  errorMessage.value = "";
  isPreviewing.value = false;
  isImporting.value = false;

  name.value = "VectoFit Bodyweight Squat v1";
  description.value =
    "Labelled bodyweight squat recordings across diagonal, frontal, and sagittal angles.";
  exerciseType.value = "bodyweight_squat";
  purpose.value = "training";
  primaryTarget.value = "squat_quality";
  secondaryTarget.value = "biomechanical_errors";
};

watch(
  () => props.isOpen,
  (isOpen) => {
    if (!isOpen) reset();
  },
);

const close = () => {
  if (isPreviewing.value || isImporting.value) return;
  emit("close");
};

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] ?? null;

  preview.value = null;
  errorMessage.value = "";

  if (!file) {
    zipFile.value = null;
    return;
  }

  if (!file.name.toLowerCase().endsWith(".zip")) {
    zipFile.value = null;
    errorMessage.value = "Please select a ZIP archive.";
    input.value = "";
    return;
  }

  zipFile.value = file;
};

const previewArchive = async () => {
  if (!zipFile.value) {
    errorMessage.value = "Select a ZIP archive first.";
    return;
  }

  isPreviewing.value = true;
  preview.value = null;
  errorMessage.value = "";

  try {
    preview.value = await datasetService.previewDatasetArchive(zipFile.value);

    if (preview.value.errors.length > 0) {
      errorMessage.value =
        "The archive has validation errors. Correct the structure and upload it again.";
    }
  } catch (error: any) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.message ||
      "Could not preview the archive.";
  } finally {
    isPreviewing.value = false;
  }
};

const commitImport = async () => {
  if (!preview.value?.upload_token || !canImport.value) return;

  isImporting.value = true;
  errorMessage.value = "";

  try {
    const result = await datasetService.commitDatasetArchive({
      upload_token: preview.value.upload_token,
      name: name.value.trim(),
      description: description.value.trim(),
      exercise_type: exerciseType.value,
      purpose: purpose.value,
      primary_target: primaryTarget.value.trim(),
      secondary_target: secondaryTarget.value.trim(),
    });

    if (result.queue_failures.length > 0) {
      errorMessage.value =
        `${result.queue_failures.length} video(s) could not be queued.` +
        "Inspect their status before training.";
    }

    emit("imported", result.dataset.name, result.imported_videos);

    emit("close");
  } catch (error: any) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.message ||
      "Dataset import failed.";
  } finally {
    isImporting.value = false;
  }
};
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="import-overlay" @click.self="close">
      <section
        class="import-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-title"
      >
        <header class="import-header">
          <div>
            <span class="eyebrow">VECTOFIT DATA PIPELINE</span>
            <h2 id="import-title">Import Dataset</h2>
            <p>
              Upload a ZIP archive, review its manifest, then queue video
              processing.
            </p>
          </div>

          <button
            class="close-button"
            type="button"
            :disabled="isImporting || isPreviewing"
            @click="close"
          >
            ✕
          </button>
        </header>

        <div class="import-body">
          <section class="import-section">
            <h3>1. Dataset information</h3>

            <div class="form-grid">
              <label>
                Dataset name
                <input v-model="name" maxlength="50" required />
              </label>

              <label>
                Exercise
                <select v-model="exerciseType">
                  <option value="bodyweight_squat">Bodyweight Squat</option>
                  <option value="goblet_squat">Goblet Squat</option>
                </select>
              </label>

              <label class="full-width">
                Description
                <textarea v-model="description" rows="2" />
              </label>
            </div>
          </section>

          <section class="import-section">
            <h3>2. Upload ZIP archive</h3>

            <p class="section-hint">
              Supported video formats: MP4, MOV, M4V, and AVI. The class and
              camera angle must be recognizable from folders or filenames.
            </p>

            <label class="file-picker">
              <span class="file-picker-icon">↑</span>
              <strong>
                {{ zipFile?.name || "Choose dataset ZIP" }}
              </strong>
              <small>
                {{
                  zipFile
                    ? `${(zipFile.size / 1024 / 1024).toFixed(1)} MB`
                    : "One archive containing your videos"
                }}
              </small>

              <input
                type="file"
                accept=".zip,application/zip"
                :disabled="isImporting || isPreviewing"
                @change="handleFileChange"
              />
            </label>

            <p class="section-hint">
              Good/bad labels are inherited by extracted repetitions. Ensure
              each clip consistently represents its folder label.
            </p>

            <button
              class="secondary-button"
              type="button"
              :disabled="!zipFile || isPreviewing || isImporting"
              @click="previewArchive"
            >
              {{ isPreviewing ? "Inspecting archive..." : "Preview archive" }}
            </button>
          </section>

          <section v-if="preview" class="import-section">
            <h3>3. Review manifest</h3>

            <div class="manifest-summary">
              <div>
                <span>Recognized videos</span>
                <strong>{{ preview.file_count }}</strong>
              </div>

              <div>
                <span>Participants</span>
                <strong>{{ preview.participant_count }}</strong>
              </div>

              <div>
                <span>Good videos</span>
                <strong>{{ preview.by_label.good }}</strong>
              </div>

              <div>
                <span>Bad videos</span>
                <strong>{{ preview.by_label.bad }}</strong>
              </div>
            </div>

            <div class="angle-summary">
              <span>Diagonal: {{ preview.by_angle.diagonal }}</span>
              <span>Frontal: {{ preview.by_angle.frontal }}</span>
              <span>Sagittal: {{ preview.by_angle.sagittal }}</span>
            </div>

            <div v-if="preview.errors.length" class="message error">
              <strong>Cannot import yet</strong>
              <ul>
                <li v-for="item in preview.errors" :key="item">
                  {{ item }}
                </li>
              </ul>
            </div>

            <div v-if="preview.warnings.length" class="message warning">
              <strong>Review these warnings</strong>
              <ul>
                <li v-for="item in preview.warnings" :key="item">
                  {{ item }}
                </li>
              </ul>
            </div>

            <div v-if="preview.files.length" class="manifest-table-wrapper">
              <table class="manifest-table">
                <thead>
                  <tr>
                    <th>Participant</th>
                    <th>View</th>
                    <th>Label</th>
                    <th>Archive path</th>
                  </tr>
                </thead>

                <tbody>
                  <tr v-for="file in preview.files" :key="file.archive_path">
                    <td>{{ file.participant_code }}</td>
                    <td>{{ file.view_angle }}</td>
                    <td>
                      <span
                        :class="[
                          'label-chip',
                          file.source_label ? 'good' : 'bad',
                        ]"
                      >
                        {{ file.source_label ? "Good" : "Bad" }}
                      </span>
                    </td>
                    <td class="path-cell">{{ file.archive_path }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <p v-if="errorMessage" class="message error">
            {{ errorMessage }}
          </p>
        </div>

        <footer class="import-footer">
          <button
            class="secondary-button"
            type="button"
            :disabled="isImporting || isPreviewing"
            @click="close"
          >
            Cancel
          </button>

          <button
            class="primary-button"
            type="button"
            :disabled="!canImport"
            @click="commitImport"
          >
            {{
              isImporting ? "Importing and queueing..." : "Import and process"
            }}
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.import-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
  background: rgba(24, 24, 27, 0.55);
  backdrop-filter: blur(4px);
}

.import-modal {
  display: flex;
  flex-direction: column;
  width: min(100%, 1000px);
  max-height: 92vh;
  overflow: hidden;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 14px;
  background: var(--vf-surface, #ffffff);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.2);
  font-family: "Segoe UI", Arial, sans-serif;
}

.import-header,
.import-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
}

.import-header {
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
}

.import-header h2 {
  margin: 5px 0;
  font-size: 22px;
  color: var(--vf-dark, #18181b);
}

.import-header p,
.section-hint {
  margin: 0;
  color: var(--vf-muted, #71717a);
  font-size: 12px;
  line-height: 1.5;
}

.eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--vf-orange, #f97316);
}

.close-button {
  border: 0;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
}

.import-body {
  padding: 20px 24px;
  overflow-y: auto;
}

.import-section + .import-section {
  margin-top: 24px;
  padding-top: 22px;
  border-top: 1px solid var(--vf-border-light, #f1f1f2);
}

.import-section h3 {
  margin: 0 0 13px;
  color: var(--vf-dark, #18181b);
  font-size: 14px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--vf-text, #27272a);
  font-size: 11px;
  font-weight: 700;
}

.form-grid input,
.form-grid select,
.form-grid textarea {
  box-sizing: border-box;
  width: 100%;
  padding: 10px 11px;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 7px;
  background: #ffffff;
  color: var(--vf-text, #27272a);
  font: inherit;
  font-weight: 400;
}

.full-width {
  grid-column: 1 / -1;
}

.file-picker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin: 12px 0;
  padding: 24px;
  border: 1px dashed #fdba74;
  border-radius: 10px;
  background: #fffaf6;
  color: var(--vf-text, #27272a);
  cursor: pointer;
}

.file-picker input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.file-picker-icon {
  font-size: 26px;
  color: var(--vf-orange, #f97316);
}

.file-picker strong {
  max-width: 100%;
  overflow-wrap: anywhere;
  font-size: 12px;
}

.file-picker small {
  color: var(--vf-muted, #71717a);
  font-size: 10px;
}

.manifest-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.manifest-summary > div {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 13px;
  border: 1px solid var(--vf-border-light, #f1f1f2);
  border-radius: 8px;
}

.manifest-summary span {
  color: var(--vf-muted, #71717a);
  font-size: 10px;
}

.manifest-summary strong {
  color: var(--vf-dark, #18181b);
  font-size: 21px;
}

.angle-summary {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
  color: var(--vf-muted, #71717a);
  font-size: 11px;
}

.angle-summary span {
  padding: 7px 10px;
  border-radius: 6px;
  background: #f4f4f5;
}

.message {
  margin-top: 14px;
  padding: 12px;
  border-radius: 8px;
  font-size: 11px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.message.error {
  background: #fef2f2;
  color: #b91c1c;
}

.message.warning {
  background: #fff7ed;
  color: #9a3412;
}

.message ul {
  margin: 7px 0 0;
  padding-left: 19px;
}

.manifest-table-wrapper {
  max-height: 300px;
  margin-top: 14px;
  overflow: auto;
  border: 1px solid var(--vf-border-light, #f1f1f2);
  border-radius: 8px;
}

.manifest-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10px;
}

.manifest-table th,
.manifest-table td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  text-align: left;
}

.manifest-table th {
  position: sticky;
  top: 0;
  background: #fafafa;
}

.path-cell {
  max-width: 340px;
  overflow-wrap: anywhere;
  color: var(--vf-muted, #71717a);
}

.label-chip {
  display: inline-block;
  padding: 4px 7px;
  border-radius: 5px;
  font-weight: 700;
}

.label-chip.good {
  background: #f0fdf4;
  color: #15803d;
}

.label-chip.bad {
  background: #fef2f2;
  color: #b91c1c;
}

.import-footer {
  justify-content: flex-end;
  border-top: 1px solid var(--vf-border-light, #f1f1f2);
}

@media (max-width: 700px) {
  .import-overlay {
    padding: 8px;
  }

  .import-header,
  .import-footer {
    padding: 16px;
  }

  .import-body {
    padding: 16px;
  }

  .form-grid,
  .manifest-summary {
    grid-template-columns: 1fr;
  }

  .import-footer {
    align-items: stretch;
    flex-direction: column-reverse;
  }
}
</style>
