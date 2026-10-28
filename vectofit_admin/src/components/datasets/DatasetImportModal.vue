<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  datasetService,
  type DatasetImportPreview,
} from "../../services/datasetService";

const props = defineProps<{ isOpen: boolean }>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "imported", datasetName: string, videoCount: number): void;
}>();

type ReviewPolicy = "source" | "all" | "subset";
type SelectionMethod = "stratified" | "manual";

const DEFAULT_NAME = "VectoFit Bodyweight Squat v1";
const DEFAULT_DESCRIPTION =
  "Labelled bodyweight squat recordings across diagonal, frontal, and sagittal views.";

const zipInput = ref<HTMLInputElement | null>(null);
const zipFile = ref<File | null>(null);
const preview = ref<DatasetImportPreview | null>(null);

const name = ref(DEFAULT_NAME);
const description = ref(DEFAULT_DESCRIPTION);
const exerciseType = ref("bodyweight_squat");
const purpose = ref("training");
const primaryTarget = ref("squat_quality");
const secondaryTarget = ref("biomechanical_errors");

const reviewPolicy = ref<ReviewPolicy>("subset");
const selectionMethod = ref<SelectionMethod>("stratified");
const reviewCount = ref(10);
const randomSeed = ref(42);
const selectedVideoPaths = ref<string[]>([]);

const isPreviewing = ref(false);
const isImporting = ref(false);
const importCompleted = ref(false);

const errorMessage = ref("");
const outcomeMessage = ref("");

const isBusy = computed(() => isPreviewing.value || isImporting.value);

const manifestFiles = computed(() => preview.value?.manifest.files ?? []);

const reviewableFiles = computed(() =>
  manifestFiles.value.filter((file) => Boolean(file.archive_path)),
);

const effectiveReviewCount = computed(() => {
  if (reviewPolicy.value === "source") return 0;
  if (reviewPolicy.value === "all") return reviewableFiles.value.length;

  return selectedVideoPaths.value.length;
});

const untouchedCount = computed(
  () => reviewableFiles.value.length - effectiveReviewCount.value,
);

const canGenerateSelection = computed(
  () =>
    reviewPolicy.value === "subset" &&
    selectionMethod.value === "stratified" &&
    reviewableFiles.value.length > 0,
);

const canImportReason = computed(() => {
  if (isBusy.value) return "Import is in progress.";
  if (importCompleted.value) return "This archive has already been imported.";
  if (!zipFile.value) return "Choose a ZIP archive to begin.";
  if (!name.value.trim()) return "Enter a dataset name.";

  if (!preview.value?.upload_token) {
    return "Preview the archive before importing.";
  }

  if (preview.value.manifest.errors.length > 0) {
    return "The archive has validation errors.";
  }

  if (reviewPolicy.value === "subset" && effectiveReviewCount.value === 0) {
    return "Select at least one video for manual review.";
  }

  return "";
});

const canImport = computed(() => !canImportReason.value);

function reset() {
  zipFile.value = null;
  preview.value = null;

  errorMessage.value = "";
  outcomeMessage.value = "";

  isPreviewing.value = false;
  isImporting.value = false;
  importCompleted.value = false;

  reviewPolicy.value = "subset";
  selectionMethod.value = "stratified";
  reviewCount.value = 10;
  randomSeed.value = 42;
  selectedVideoPaths.value = [];

  name.value = DEFAULT_NAME;
  description.value = DEFAULT_DESCRIPTION;
  exerciseType.value = "bodyweight_squat";
  purpose.value = "training";
  primaryTarget.value = "squat_quality";
  secondaryTarget.value = "biomechanical_errors";

  if (zipInput.value) zipInput.value.value = "";
}

watch(
  () => props.isOpen,
  (isOpen) => {
    if (!isOpen && !isBusy.value) reset();
  },
);

function close() {
  if (isBusy.value) return;
  emit("close");
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] ?? null;

  preview.value = null;
  selectedVideoPaths.value = [];
  errorMessage.value = "";
  outcomeMessage.value = "";
  importCompleted.value = false;

  if (!file) {
    zipFile.value = null;
    return;
  }

  if (!file.name.toLowerCase().endsWith(".zip")) {
    zipFile.value = null;
    input.value = "";
    errorMessage.value = "Please select a ZIP archive.";
    return;
  }

  zipFile.value = file;
}

function getErrorMessage(error: unknown): string | null {
  if (!error || typeof error !== "object") {
    return error instanceof Error ? error.message : null;
  }

  const candidate = error as {
    message?: unknown;
    response?: { data?: Record<string, unknown> };
  };

  const data = candidate.response?.data;

  for (const value of [
    data?.detail,
    data?.message,
    data?.error,
    ...Object.values(data ?? {}),
  ]) {
    if (typeof value === "string" && value.trim()) {
      return value;
    }

    if (Array.isArray(value)) {
      const message = value.find(
        (item): item is string =>
          typeof item === "string" && item.trim().length > 0,
      );

      if (message) return message;
    }
  }

  return typeof candidate.message === "string" ? candidate.message : null;
}

function hashString(value: string): number {
  let hash = 2166136261;

  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return hash >>> 0;
}

function generateStratifiedSelection(): string[] {
  const files = reviewableFiles.value;
  if (!files.length) return [];

  const count = Math.max(
    1,
    Math.min(files.length, Math.floor(reviewCount.value)),
  );

  const groups = new Map<string, typeof files>();

  for (const file of files) {
    const label = file.source_label ? "good" : "bad";
    const angle = file.view_angle || "unknown";
    const key = `${label}:${angle}`;

    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(file);
  }

  const seed = String(randomSeed.value);

  for (const [key, group] of groups) {
    group.sort(
      (a, b) =>
        hashString(`${seed}:${key}:${a.archive_path}`) -
        hashString(`${seed}:${key}:${b.archive_path}`),
    );
  }

  const orderedGroups = [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, group]) => group);

  const selected: string[] = [];
  let cursor = 0;

  while (
    selected.length < count &&
    orderedGroups.some((group) => group.length > 0)
  ) {
    const group = orderedGroups[cursor % orderedGroups.length];

    if (group.length > 0) {
      selected.push(group.shift()!.archive_path);
    }

    cursor += 1;
  }

  return selected;
}

function generateSelection() {
  if (selectionMethod.value !== "stratified") return;

  selectedVideoPaths.value = generateStratifiedSelection();
}

function toggleVideo(path: string, checked: boolean) {
  if (checked) {
    if (!selectedVideoPaths.value.includes(path)) {
      selectedVideoPaths.value = [...selectedVideoPaths.value, path];
    }
  } else {
    selectedVideoPaths.value = selectedVideoPaths.value.filter(
      (item) => item !== path,
    );
  }
}

function toggleAllVideos() {
  const allPaths = reviewableFiles.value.map((file) => file.archive_path);

  selectedVideoPaths.value =
    selectedVideoPaths.value.length === allPaths.length ? [] : allPaths;
}

watch([reviewPolicy, selectionMethod], ([policy, method]) => {
  if (policy === "all") {
    selectedVideoPaths.value = reviewableFiles.value.map(
      (file) => file.archive_path,
    );
  } else if (policy === "source") {
    selectedVideoPaths.value = [];
  } else if (method === "stratified" && preview.value) {
    generateSelection();
  }
});

async function previewArchive() {
  if (isBusy.value) return;

  if (!zipFile.value) {
    errorMessage.value = "Select a ZIP archive first.";
    return;
  }

  isPreviewing.value = true;
  preview.value = null;
  selectedVideoPaths.value = [];
  errorMessage.value = "";
  outcomeMessage.value = "";

  try {
    const result = await datasetService.previewDatasetArchive(zipFile.value);

    preview.value = result;

    if (result.manifest.errors.length > 0) {
      errorMessage.value =
        "The archive has validation errors. Correct the archive and upload it again.";
    } else if (!result.upload_token) {
      errorMessage.value =
        "The preview did not return an upload token. Please preview again.";
    } else if (reviewPolicy.value === "subset") {
      generateSelection();
    } else if (reviewPolicy.value === "all") {
      selectedVideoPaths.value = reviewableFiles.value.map(
        (file) => file.archive_path,
      );
    }
  } catch (error: unknown) {
    errorMessage.value =
      getErrorMessage(error) ?? "Could not preview the archive.";
  } finally {
    isPreviewing.value = false;
  }
}

async function commitImport() {
  const currentPreview = preview.value;

  if (!currentPreview?.upload_token || !canImport.value) {
    return;
  }

  if (isBusy.value || importCompleted.value) return;

  if (!canImport.value) {
    errorMessage.value = canImportReason.value;
    return;
  }

  isImporting.value = true;
  errorMessage.value = "";
  outcomeMessage.value = "";

  try {
    const result = await datasetService.commitDatasetArchive({
      upload_token: currentPreview.upload_token,
      name: name.value.trim(),
      description: description.value.trim(),
      exercise_type: exerciseType.value,
      purpose: purpose.value,
      primary_target: primaryTarget.value.trim(),
      secondary_target: secondaryTarget.value.trim(),
      review_policy: reviewPolicy.value,
      selection_method: selectionMethod.value,
      review_count:
        reviewPolicy.value === "subset"
          ? effectiveReviewCount.value
          : undefined,
      random_seed:
        reviewPolicy.value === "subset" &&
        selectionMethod.value === "stratified"
          ? randomSeed.value
          : undefined,
      selected_video_paths:
        reviewPolicy.value === "subset" ? [...selectedVideoPaths.value] : [],
    });

    importCompleted.value = true;

    emit("imported", result.dataset.name, result.imported_videos);

    if (result.queue_failures.length > 0) {
      outcomeMessage.value =
        `Dataset "${result.dataset.name}" was imported, but ` +
        `${result.queue_failures.length} video(s) could not be queued. ` +
        `Imported: ${result.imported_videos}. ` +
        `Queued: ${result.queued_videos}. ` +
        "Check video processing statuses before training.";

      return;
    }

    emit("close");
  } catch (error: unknown) {
    errorMessage.value = getErrorMessage(error) ?? "Dataset import failed.";
  } finally {
    isImporting.value = false;
  }
}
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
              Upload a ZIP archive, review its manifest, and configure
              annotation.
            </p>
          </div>

          <button
            type="button"
            class="close-button"
            aria-label="Close import dialog"
            :disabled="isBusy"
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
                <input
                  v-model="name"
                  maxlength="50"
                  required
                  autocomplete="off"
                  placeholder="Enter dataset name"
                />
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
                <textarea
                  v-model="description"
                  rows="2"
                  placeholder="Describe the dataset"
                />
              </label>
            </div>
          </section>

          <section class="import-section">
            <h3>2. Upload ZIP archive</h3>

            <p class="section-hint">
              Supported formats: MP4, MOV, M4V, and AVI. Class labels and camera
              angles must be recognizable from archive folders or filenames.
            </p>

            <label class="file-picker" for="dataset-archive">
              <span class="file-picker-icon" aria-hidden="true">↑</span>
              <strong>{{ zipFile?.name || "Choose dataset ZIP" }}</strong>
              <small>
                {{
                  zipFile
                    ? `${(zipFile.size / 1024 / 1024).toFixed(1)} MB`
                    : "Select a ZIP archive containing your videos"
                }}
              </small>

              <input
                id="dataset-archive"
                ref="zipInput"
                type="file"
                accept=".zip,application/zip"
                :disabled="isBusy || importCompleted"
                @change="handleFileChange"
              />
            </label>

            <p class="section-hint">
              ZIP labels are source-provided labels. They do not mean a human
              has reviewed the repetitions.
            </p>

            <button
              type="button"
              class="secondary-button preview-button"
              :disabled="!zipFile || isBusy || importCompleted"
              @click="previewArchive"
            >
              {{ isPreviewing ? "Inspecting archive..." : "Preview archive" }}
            </button>
          </section>

          <template v-if="preview">
            <section class="import-section">
              <h3>3. Review manifest</h3>

              <div class="manifest-summary">
                <div>
                  <span>Recognized videos</span>
                  <strong>{{ preview.manifest.file_count }}</strong>
                </div>
                <div>
                  <span>Participants</span>
                  <strong>{{ preview.manifest.participant_count }}</strong>
                </div>
                <div>
                  <span>Good videos</span>
                  <strong>{{ preview.manifest.by_label.good }}</strong>
                </div>
                <div>
                  <span>Bad videos</span>
                  <strong>{{ preview.manifest.by_label.bad }}</strong>
                </div>
              </div>

              <div class="angle-summary">
                <span>Diagonal: {{ preview.manifest.by_angle.diagonal }}</span>
                <span>Frontal: {{ preview.manifest.by_angle.frontal }}</span>
                <span>Sagittal: {{ preview.manifest.by_angle.sagittal }}</span>
              </div>

              <div
                v-if="preview.manifest.errors.length"
                class="message error"
                role="alert"
              >
                <strong>Cannot import yet</strong>
                <ul>
                  <li v-for="item in preview.manifest.errors" :key="item">
                    {{ item }}
                  </li>
                </ul>
              </div>

              <div
                v-if="preview.manifest.warnings.length"
                class="message warning"
                role="status"
              >
                <strong>Review these warnings</strong>
                <ul>
                  <li v-for="item in preview.manifest.warnings" :key="item">
                    {{ item }}
                  </li>
                </ul>
              </div>
            </section>

            <section class="import-section">
              <h3>4. Labeling &amp; review policy</h3>

              <label class="policy-option">
                <input v-model="reviewPolicy" type="radio" value="source" />
                <span>
                  <strong>Use ZIP labels only</strong>
                  <small
                    >Inherit source labels; do not select videos for manual
                    review.</small
                  >
                </span>
              </label>

              <label class="policy-option">
                <input v-model="reviewPolicy" type="radio" value="all" />
                <span>
                  <strong>Review every video</strong>
                  <small
                    >Select all imported videos for manual annotation.</small
                  >
                </span>
              </label>

              <label class="policy-option">
                <input v-model="reviewPolicy" type="radio" value="subset" />
                <span>
                  <strong>Review a selected subset</strong>
                  <small
                    >Select individual videos or sample across labels and
                    views.</small
                  >
                </span>
              </label>

              <div v-if="reviewPolicy === 'subset'" class="selection-settings">
                <label>
                  Selection method
                  <select v-model="selectionMethod">
                    <option value="stratified">Stratified random</option>
                    <option value="manual">Manual selection</option>
                  </select>
                </label>

                <template v-if="selectionMethod === 'stratified'">
                  <label>
                    Videos to review
                    <input
                      v-model.number="reviewCount"
                      type="number"
                      min="1"
                      :max="reviewableFiles.length || 1"
                    />
                  </label>

                  <label>
                    Random seed
                    <input v-model.number="randomSeed" type="number" />
                  </label>

                  <button
                    type="button"
                    class="secondary-button"
                    :disabled="!canGenerateSelection || isBusy"
                    @click="generateSelection"
                  >
                    Generate selection
                  </button>
                </template>

                <button
                  v-else
                  type="button"
                  class="secondary-button"
                  @click="toggleAllVideos"
                >
                  {{
                    selectedVideoPaths.length === reviewableFiles.length
                      ? "Clear selection"
                      : "Select all videos"
                  }}
                </button>
              </div>

              <div class="review-summary">
                <div>
                  <span>Selected for review</span>
                  <strong>{{ effectiveReviewCount }}</strong>
                </div>
                <div>
                  <span>Left untouched</span>
                  <strong>{{ untouchedCount }}</strong>
                </div>
              </div>

              <p class="section-hint">
                Selection is based on whole videos, not individual repetitions.
                Source labels remain distinct from human annotation status.
              </p>

              <div class="manifest-table-wrapper">
                <table class="manifest-table">
                  <thead>
                    <tr>
                      <th
                        v-if="
                          reviewPolicy === 'subset' &&
                          selectionMethod === 'manual'
                        "
                      >
                        Review
                      </th>
                      <th>Participant</th>
                      <th>View</th>
                      <th>ZIP label</th>
                      <th>Review state</th>
                      <th>Archive path</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="file in preview.manifest.files"
                      :key="file.archive_path"
                    >
                      <td
                        v-if="
                          reviewPolicy === 'subset' &&
                          selectionMethod === 'manual'
                        "
                      >
                        <input
                          type="checkbox"
                          :checked="
                            selectedVideoPaths.includes(file.archive_path)
                          "
                          :aria-label="`Review ${file.archive_path}`"
                          @change="
                            toggleVideo(
                              file.archive_path,
                              ($event.target as HTMLInputElement).checked,
                            )
                          "
                        />
                      </td>
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
                      <td>
                        {{
                          reviewPolicy === "all" ||
                          (reviewPolicy === "subset" &&
                            selectedVideoPaths.includes(file.archive_path))
                            ? "Selected for review"
                            : "Untouched"
                        }}
                      </td>
                      <td class="path-cell">{{ file.archive_path }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </template>

          <div v-if="errorMessage" class="message error" role="alert">
            {{ errorMessage }}
          </div>

          <div v-if="outcomeMessage" class="message warning" role="status">
            {{ outcomeMessage }}
          </div>
        </div>

        <footer class="import-footer">
          <p
            v-if="!canImport && !importCompleted"
            class="import-blocker"
            role="status"
          >
            {{ canImportReason }}
          </p>

          <p v-else-if="importCompleted" class="import-blocker" role="status">
            This archive has already been submitted successfully.
          </p>

          <div class="import-actions">
            <button
              type="button"
              class="secondary-button"
              :disabled="isBusy"
              @click="close"
            >
              {{ importCompleted ? "Close" : "Cancel" }}
            </button>

            <button
              type="button"
              class="primary-button"
              :disabled="!canImport"
              @click="commitImport"
            >
              <span v-if="isImporting" class="spinner" aria-hidden="true" />
              {{
                isImporting
                  ? "Importing and queueing..."
                  : importCompleted
                    ? "Import completed"
                    : "Import"
              }}
            </button>
          </div>
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
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgb(24 24 27 / 55%);
  backdrop-filter: blur(4px);
}

.import-modal {
  display: flex;
  width: min(100%, 1000px);
  max-height: 92vh;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 14px;
  background: var(--vf-surface, #fff);
  box-shadow: 0 24px 70px rgb(0 0 0 / 20%);
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
  color: var(--vf-dark, #18181b);
  font-size: 22px;
}

.import-header p,
.section-hint {
  margin: 0;
  color: var(--vf-muted, #71717a);
  font-size: 12px;
  line-height: 1.5;
}

.eyebrow {
  color: var(--vf-orange, #f97316);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.1em;
}

.close-button {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 8px;
  background: transparent;
  color: var(--vf-muted, #71717a);
  font-size: 18px;
  cursor: pointer;
}

.import-body {
  min-height: 0;
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

.form-grid,
.selection-settings {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label,
.selection-settings label {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6px;
  color: var(--vf-text, #27272a);
  font-size: 11px;
  font-weight: 700;
}

.form-grid input,
.form-grid select,
.form-grid textarea,
.selection-settings input,
.selection-settings select {
  box-sizing: border-box;
  width: 100%;
  min-height: 39px;
  padding: 10px 11px;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 7px;
  outline: none;
  background: var(--vf-surface, #fff);
  color: var(--vf-text, #27272a);
  font: inherit;
  font-weight: 400;
}

.form-grid textarea {
  resize: vertical;
}

.form-grid input:focus,
.form-grid select:focus,
.form-grid textarea:focus,
.selection-settings input:focus,
.selection-settings select:focus {
  border-color: var(--vf-orange, #f97316);
  box-shadow: 0 0 0 3px rgb(249 115 22 / 12%);
}

.full-width {
  grid-column: 1 / -1;
}

.file-picker {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  margin: 12px 0;
  padding: 24px;
  border: 1px dashed #fdba74;
  border-radius: 10px;
  background: #fffaf6;
  color: var(--vf-text, #27272a);
  text-align: center;
  cursor: pointer;
}

.file-picker-icon {
  color: var(--vf-orange, #f97316);
  font-size: 26px;
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

.file-picker input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  clip-path: inset(50%);
}

.file-picker:focus-within {
  outline: 2px solid var(--vf-orange, #f97316);
  outline-offset: 3px;
}

.preview-button {
  margin-top: 14px;
}

.policy-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 9px;
  padding: 12px;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 9px;
  cursor: pointer;
}

.policy-option input {
  margin-top: 3px;
  accent-color: var(--vf-orange, #f97316);
}

.policy-option strong,
.policy-option small {
  display: block;
}

.policy-option strong {
  color: var(--vf-dark, #18181b);
  font-size: 12px;
}

.policy-option small {
  margin-top: 4px;
  color: var(--vf-muted, #71717a);
  font-size: 11px;
  line-height: 1.5;
}

.selection-settings {
  margin-top: 14px;
  padding: 14px;
  border-radius: 9px;
  background: var(--vf-surface-muted, #fafafa);
}

.manifest-summary,
.review-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.review-summary {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 14px;
}

.manifest-summary > div,
.review-summary > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5px;
  padding: 13px;
  border: 1px solid var(--vf-border-light, #f1f1f2);
  border-radius: 8px;
}

.manifest-summary span,
.review-summary span {
  color: var(--vf-muted, #71717a);
  font-size: 10px;
}

.manifest-summary strong,
.review-summary strong {
  color: var(--vf-dark, #18181b);
  font-size: 21px;
}

.angle-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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
  flex-wrap: wrap;
  border-top: 1px solid var(--vf-border-light, #f1f1f2);
}

.import-blocker {
  flex: 1 1 220px;
  margin: 0;
  color: var(--vf-muted, #71717a);
  font-size: 11px;
  line-height: 1.5;
}

.import-actions {
  display: flex;
  flex: 0 0 auto;
  justify-content: flex-end;
  gap: 10px;
}

.primary-button,
.secondary-button {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 15px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.primary-button {
  border: none;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  color: #fff;
}

.secondary-button {
  border: 1px solid var(--vf-border, #e4e4e7);
  background: var(--vf-surface, #fff);
  color: var(--vf-text, #27272a);
}

.primary-button:disabled,
.secondary-button:disabled,
.close-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgb(255 255 255 / 45%);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 700ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 700px) {
  .import-overlay {
    align-items: flex-start;
    padding: 8px;
  }

  .import-modal {
    max-height: calc(100dvh - 16px);
  }

  .import-header,
  .import-footer,
  .import-body {
    padding: 16px;
  }

  .form-grid,
  .selection-settings,
  .manifest-summary {
    grid-template-columns: 1fr;
  }

  .import-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .import-actions {
    flex-direction: column-reverse;
  }

  .import-actions button {
    width: 100%;
  }
}
</style>
