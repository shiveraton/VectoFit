<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";

import { useDatasets } from "../../hooks/useDatasets";
import { useParticipants } from "../../hooks/useParticipants.ts";
import { useAnnotationPool } from "../../hooks/useAnnotationPool";
import { VIEW_ANGLE_BY_ID, type Dataset } from "../../services/datasetService";

import SummaryCard from "../../components/datasets/SummaryCard.vue";
import DatasetEmptyState from "../../components/datasets/DatasetEmptyState.vue";
import StructureGrid from "../../components/datasets/StructureGrid.vue";
import CreateDatasetModal from "../../components/datasets/CreateDatasetModal.vue";
import DatasetImportModal from "../../components/datasets/DatasetImportModal.vue";

const router = useRouter();

const {
  datasets,
  isLoading,
  isCreating,
  isModalOpen,
  datasetForm,
  errorMessage,
  successMessage,
  totalDatasets,
  totalSamples,
  usableDatasets,
  fetchDatasets,
  openCreateModal,
  closeCreateModal,
  handleCreateDataset,
  retryDataset,
} = useDatasets();

const { participants, fetchParticipants, createParticipant } =
  useParticipants();
const {
  filteredJobs,
  selectedJob,
  search: annotationSearch,
  statusFilter: annotationStatusFilter,
  isLoading: isAnnotationPoolLoading,
  error: annotationPoolError,
  fetchJobs: fetchAnnotationJobs,
  selectJob,
  clearSelection,
} = useAnnotationPool();

const activeTab = ref<"datasets" | "annotation-pool">("datasets");

type DatasetReviewMetrics = {
  human_reviewed_sample_count?: number | null;
  review_selected_sample_count?: number | null;
  pending_review_sample_count?: number | null;
};

const reviewMetrics = (dataset: Dataset) =>
  dataset as Dataset & DatasetReviewMetrics;

const hasSamples = (dataset: Dataset) => dataset.sample_count > 0;

const hasUnlabelledSamples = (dataset: Dataset) =>
  dataset.sample_count > dataset.labelled_sample_count;

const pendingReviewCount = (dataset: Dataset) => {
  const count = reviewMetrics(dataset).pending_review_sample_count;

  if (typeof count === "number" && Number.isFinite(count)) {
    return Math.max(0, count);
  }

  if (!isZipCollection(dataset)) {
    return 0;
  }

  return Math.max(0, dataset.sample_count - dataset.labelled_sample_count);
};

const humanReviewedSummary = (dataset: Dataset) => {
  const metrics = reviewMetrics(dataset);
  const reviewed = metrics.human_reviewed_sample_count;
  const selected = metrics.review_selected_sample_count;

  if (typeof reviewed !== "number" || !Number.isFinite(reviewed)) {
    return "Not tracked";
  }

  return typeof selected === "number" && Number.isFinite(selected)
    ? `${reviewed}/${selected}`
    : String(reviewed);
};

const zipReviewStatus = (dataset: Dataset): string => {
  const metrics = reviewMetrics(dataset);

  const selected = metrics.review_selected_sample_count;
  const reviewed = metrics.human_reviewed_sample_count;
  const pending = metrics.pending_review_sample_count;

  if (typeof selected !== "number" || !Number.isFinite(selected)) {
    return "Review tracking unavailable";
  }

  if (selected === 0) {
    return "No samples selected";
  }

  if (typeof pending === "number" && pending > 0) {
    return `${pending} pending review`;
  }

  if (
    typeof reviewed === "number" &&
    Number.isFinite(reviewed) &&
    reviewed >= selected
  ) {
    return "Review complete";
  }

  if (typeof reviewed === "number" && reviewed >= 0) {
    return "Review in progress";
  }

  return "Review status unavailable";
};

const isAnnotationReady = (dataset: Dataset) =>
  dataset.status === "READY" && hasSamples(dataset);

const isReviewComplete = (dataset: Dataset) => {
  if (!hasSamples(dataset)) return false;

  if (isZipCollection(dataset)) {
    const metrics = reviewMetrics(dataset);
    const selected = metrics.review_selected_sample_count;
    const reviewed = metrics.human_reviewed_sample_count;

    return (
      typeof selected === "number" &&
      selected > 0 &&
      typeof reviewed === "number" &&
      reviewed >= selected
    );
  }

  return !hasUnlabelledSamples(dataset);
};

const openAnnotation = (datasetId: number) => {
  router.push(`/dataset/${datasetId}/annotate`);
};

const handleAddParticipant = async () => {
  const participant = await createParticipant();

  if (participant) {
    datasetForm.value.participant = participant.id;
    console.log(`Created participant ${participant.participant_code}`);
  }
};

const handleRetryDataset = async (datasetId: number) => {
  await retryDataset(datasetId);
};

const processingDatasetCount = computed(
  () =>
    datasets.value.filter((dataset) => dataset.status === "PROCESSING").length,
);

const isImportModalOpen = ref(false);

const openImportModal = () => {
  isImportModalOpen.value = true;
};

const handleBulkImported = async (datasetName: string, videoCount: number) => {
  successMessage.value =
    `Imported ${videoCount} video(s) into "${datasetName}". ` +
    "Video processing has been queued.";

  await fetchDatasets(true);
};

function isZipCollection(dataset: Dataset): boolean {
  return !dataset.video_file && (dataset.video_count ?? 0) > 0;
}

function participantSummary(dataset: Dataset): string {
  if (isZipCollection(dataset)) {
    const count = dataset.participant_count;

    return count === null
      ? "Assigned per video"
      : `${count} participant${count === 1 ? "" : "s"}`;
  }

  return dataset.participant ? `p-${dataset.participant}` : "Unassigned";
}

function viewSummary(dataset: Dataset): string {
  if (isZipCollection(dataset)) {
    return dataset.view_angles?.length
      ? dataset.view_angles
          .map((angle) => angle.charAt(0).toUpperCase() + angle.slice(1))
          .join(",")
      : "Defined per video";
  }

  return dataset.view_angle == null
    ? ""
    : (VIEW_ANGLE_BY_ID[dataset.view_angle] ?? "Unknown");
}

function videoSummary(dataset: Dataset): string {
  if (!isZipCollection(dataset)) {
    return dataset.video_file ? "1 video" : "";
  }

  const total = dataset.video_count ?? 0;
  const ready = dataset.ready_video_count ?? 0;
  const failed = dataset.failed_video_count ?? 0;

  return `${ready}/${total} ready - ${failed} failed`;
}

function formatActivityDate(value: string): string {
  return new Date(value).toLocaleString();
}

function annotationStatusLabel(status: string): string {
  return status.replace("_", " ");
}

onMounted(async () => {
  await Promise.all([
    fetchParticipants(),
    fetchDatasets(),
    fetchAnnotationJobs(),
  ]);
});
</script>

<template>
  <div class="dataset-page">
    <header class="page-header">
      <div class="page-heading">
        <div class="eyebrow">
          <span class="eyebrow-dot"></span>
          VECTOFIT DATA PIPELINE
        </div>

        <h1>Datasets</h1>

        <p>Manage datasets used for VectoFit model training and evaluation.</p>
      </div>

      <div class="page-actions">
        <button class="secondary-button" type="button" @click="openCreateModal">
          Add Single Video
        </button>

        <button class="primary-button" type="button" @click="openImportModal">
          <span class="button-icon">↑</span>
          Import Dataset
        </button>
      </div>
    </header>

    <nav class="page-tabs" aria-label="Dataset views">
      <button
        type="button"
        class="page-tab"
        :class="{ active: activeTab === 'datasets' }"
        @click="activeTab = 'datasets'"
      >
        Datasets
      </button>

      <button
        type="button"
        class="page-tab"
        :class="{ active: activeTab === 'annotation-pool' }"
        @click="activeTab = 'annotation-pool'"
      >
        Annotation Pool
      </button>
    </nav>

    <div v-if="successMessage" class="feedback-message success">
      {{ successMessage }}
    </div>

    <div v-if="errorMessage" class="feedback-message error">
      {{ errorMessage }}
    </div>

    <section v-if="activeTab === 'datasets'" class="summary-grid">
      <SummaryCard
        label="Datasets"
        :value="totalDatasets"
        description="Registered datasets"
        icon="D"
        variant="samples"
      />

      <SummaryCard
        label="Samples"
        :value="totalSamples"
        description="Completed squat repetitions"
        icon="Σ"
        variant="samples"
      />

      <SummaryCard
        label="Training Ready"
        :value="usableDatasets.length"
        description="Datasets with labelled samples"
        icon="✓"
        variant="correct"
      />

      <SummaryCard
        label="Processing"
        :value="processingDatasetCount"
        description="Currently being processed"
        icon="↻"
        variant="version"
      />
    </section>

    <section v-if="activeTab === 'datasets'" class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker"></div>

          <div>
            <h2>Datasets</h2>
            <p>Registered exercise data and preprocessing status.</p>
          </div>
        </div>
      </div>

      <DatasetEmptyState
        v-if="!isLoading && datasets.length === 0"
        @action="openCreateModal"
      />

      <div v-else-if="isLoading" class="loading-state" aria-live="polite">
        <span class="loading-dot" aria-hidden="true"></span>
        Loading datasets...
      </div>

      <div v-else class="dataset-table-wrapper">
        <table class="dataset-table">
          <thead>
            <tr>
              <th>Dataset</th>
              <th>Type</th>
              <th>Participants</th>
              <th>View Angles</th>
              <th>Exercise</th>
              <th>Purpose</th>
              <th>Videos</th>
              <th>Samples</th>
              <th>
                <span
                  title="A sample may have inherited its label from a ZIP folder; this does not prove human review."
                >
                  Labelled
                </span>
              </th>
              <th>Human reviewed</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="dataset in datasets" :key="dataset.id">
              <td>
                <div class="dataset-name">
                  <strong>{{ dataset.name }}</strong>
                  <span class="dataset-id">#{{ dataset.id }}</span>
                </div>
              </td>

              <td>
                <span
                  class="exercise-value"
                  :title="
                    isZipCollection(dataset)
                      ? 'A collection of individual video records'
                      : 'A dataset containing one video'
                  "
                >
                  {{ isZipCollection(dataset) ? "ZIP" : "Single video" }}
                </span>
              </td>

              <td>
                <span
                  v-if="!isZipCollection(dataset) && dataset.participant"
                  class="participant-value"
                >
                  P-{{ dataset.participant }}
                </span>

                <span v-else class="muted-value">
                  {{ participantSummary(dataset) }}
                </span>
              </td>

              <td>
                <span class="muted-value">
                  {{ viewSummary(dataset) }}
                </span>
              </td>

              <td>
                {{ dataset.exercise_type }}
              </td>

              <td>
                {{ dataset.purpose }}
              </td>

              <td>
                <span class="sample-count">
                  {{ videoSummary(dataset) }}
                </span>
              </td>

              <td>
                <span class="sample-count">
                  {{ dataset.sample_count }}
                </span>
              </td>

              <td>
                <span
                  class="labelled-count"
                  :title="`${dataset.labelled_sample_count} of ${dataset.sample_count} repetitions have a binary label; labels may be inherited from ZIP folders.`"
                >
                  <strong>{{ dataset.labelled_sample_count }}</strong>
                  /
                  {{ dataset.sample_count }}
                </span>
              </td>

              <td>
                <span class="labelled-count">
                  {{ humanReviewedSummary(dataset) }}
                </span>
              </td>

              <td>
                <span
                  class="status-badge"
                  :class="`status-${dataset.status.toLowerCase()}`"
                >
                  <span v-if="dataset.status === 'PROCESSING'"></span>

                  {{ dataset.status }}
                </span>
              </td>

              <td>
                <div class="action-cell">
                  <button
                    v-if="isAnnotationReady(dataset)"
                    type="button"
                    class="action-button"
                    @click="openAnnotation(dataset.id)"
                  >
                    Annotate
                  </button>

                  <span
                    v-else-if="
                      dataset.status === 'READY' && isReviewComplete(dataset)
                    "
                    class="action-complete"
                  >
                    {{
                      isZipCollection(dataset) ? "Review complete" : "Complete"
                    }}
                  </span>

                  <span
                    v-else-if="
                      dataset.status === 'READY' && isZipCollection(dataset)
                    "
                    class="muted-value"
                    title="ZIP folder labels are source labels. Manual-review completion is tracked separately."
                  >
                    {{ zipReviewStatus(dataset) }}
                  </span>

                  <span
                    v-else-if="dataset.status === 'PROCESSING'"
                    class="processing-state"
                  >
                    <span class="processing-spinner"></span>
                  </span>

                  <span
                    v-else-if="
                      isZipCollection(dataset) &&
                      ['PARTIAL', 'FAILED'].includes(dataset.status)
                    "
                    class="muted-value"
                    :title="`${dataset.failed_video_count ?? 0} video(s) failed processing`"
                  >
                    Check videos
                  </span>

                  <button
                    v-else-if="
                      dataset.status === 'FAILED' && !isZipCollection(dataset)
                    "
                    type="button"
                    class="action-button retry-button"
                    @click="handleRetryDataset(dataset.id)"
                  >
                    Retry
                  </button>

                  <span
                    v-else-if="dataset.status === 'PENDING'"
                    class="muted-value"
                  >
                    Queued
                  </span>

                  <span v-else class="muted-value"></span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'datasets'" class="content-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker"></div>

          <div>
            <h2>Dataset Structure</h2>
            <p>Each completed squat repetition represents one sample.</p>
          </div>
        </div>
      </div>

      <StructureGrid />
    </section>

    <section v-else class="content-card annotation-pool-card">
      <div class="section-header">
        <div class="section-title-row">
          <div class="section-marker"></div>

          <div>
            <h2>Annotation Pool</h2>
            <p>Dataset-level annotation jobs and their complete activity log.</p>
          </div>
        </div>

        <button
          type="button"
          class="secondary-button"
          :disabled="isAnnotationPoolLoading"
          @click="fetchAnnotationJobs"
        >
          Refresh
        </button>
      </div>

      <div class="annotation-pool-toolbar">
        <input
          v-model="annotationSearch"
          class="pool-search"
          type="search"
          placeholder="Search dataset or annotator"
          aria-label="Search annotation jobs"
        />

        <select
          v-model="annotationStatusFilter"
          class="pool-filter"
          aria-label="Filter annotation jobs by status"
        >
          <option value="ALL">All statuses</option>
          <option value="QUEUED">Queued</option>
          <option value="IN_PROGRESS">In progress</option>
          <option value="COMPLETED">Completed</option>
          <option value="NO_SAMPLES">No samples</option>
        </select>
      </div>

      <div v-if="annotationPoolError" class="pool-message error">
        {{ annotationPoolError }}
      </div>

      <div v-else-if="isAnnotationPoolLoading" class="loading-state">
        <span class="loading-dot" aria-hidden="true"></span>
        Loading annotation activity...
      </div>

      <div v-else-if="filteredJobs.length === 0" class="empty-state">
        No annotation jobs match the current filters.
      </div>

      <div v-else class="annotation-pool-layout">
        <div class="pool-table-wrapper">
          <table class="dataset-table pool-table">
            <thead>
              <tr>
                <th>Dataset</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Activity</th>
                <th>Annotators</th>
                <th>Updated</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="job in filteredJobs"
                :key="job.id"
                class="pool-row"
                :class="{ selected: selectedJob?.id === job.id }"
                tabindex="0"
                @click="selectJob(job)"
                @keydown.enter="selectJob(job)"
              >
                <td>
                  <div class="dataset-name">
                    <strong>{{ job.name }}</strong>
                    <span class="dataset-id">Job #{{ job.id }}</span>
                  </div>
                </td>
                <td>
                  <span
                    class="pool-status"
                    :class="`pool-status-${job.job_status.toLowerCase()}`"
                  >
                    {{ annotationStatusLabel(job.job_status) }}
                  </span>
                </td>
                <td>
                  <span class="sample-count">
                    {{ job.reviewed_count }} / {{ job.sample_count }}
                  </span>
                  <span class="pool-subtext">samples reviewed</span>
                </td>
                <td>
                  <span class="sample-count">{{ job.activity_count }}</span>
                  <span class="pool-subtext">logged actions</span>
                </td>
                <td>
                  <span class="pool-subtext">
                    {{
                      job.annotators.length
                        ? job.annotators
                            .map((item) => item.annotator?.username ?? "Unassigned")
                            .join(", ")
                        : "No activity"
                    }}
                  </span>
                </td>
                <td>
                  <span class="pool-subtext">
                    {{ formatActivityDate(job.last_activity_at) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <aside v-if="selectedJob" class="pool-details">
          <div class="pool-details-header">
            <div>
              <span class="dataset-id">DATASET #{{ selectedJob.id }}</span>
              <h3>{{ selectedJob.name }}</h3>
            </div>

            <button
              type="button"
              class="close-details"
              aria-label="Close annotation details"
              @click="clearSelection"
            >
              ×
            </button>
          </div>

          <div class="pool-metrics">
            <div>
              <strong>{{ selectedJob.sample_count }}</strong>
              <span>Samples</span>
            </div>
            <div>
              <strong>{{ selectedJob.reviewed_count }}</strong>
              <span>Reviewed</span>
            </div>
            <div>
              <strong>{{ selectedJob.pending_count }}</strong>
              <span>Pending</span>
            </div>
          </div>

          <h4>Activity log</h4>

          <div v-if="selectedJob.activity.length === 0" class="pool-subtext">
            No annotation activity has been logged yet.
          </div>

          <ul v-else class="activity-list">
            <li v-for="activity in selectedJob.activity" :key="activity.id">
              <div>
                <strong>Sample #{{ activity.sample_id }}</strong>
                <span>
                  {{ activity.annotator?.username ?? "Unassigned" }}
                </span>
              </div>
              <time :datetime="activity.created_at">
                {{ formatActivityDate(activity.created_at) }}
              </time>
            </li>
          </ul>
        </aside>
      </div>
    </section>

    <CreateDatasetModal
      :is-open="isModalOpen"
      :is-submitting="isCreating"
      :form="datasetForm"
      :participants="participants"
      @create-participant="handleAddParticipant"
      @close="closeCreateModal"
      @submit="handleCreateDataset"
    />

    <DatasetImportModal
      :is-open="isImportModalOpen"
      @close="isImportModalOpen = false"
      @imported="handleBulkImported"
    />
  </div>
</template>

<style scoped>
.dataset-page {
  min-height: 100%;
  padding: 32px;
  background: var(--vf-background);
  font-family: "Segoe UI", Arial, sans-serif;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 28px;
}

.page-heading {
  display: flex;
  flex-direction: column;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--vf-border, #e4e4e7);
}

.page-tab {
  padding: 10px 14px;
  color: var(--vf-muted, #71717a);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.page-tab:hover,
.page-tab.active {
  color: var(--vf-orange-dark, #c2410c);
}

.page-tab.active {
  border-bottom-color: var(--vf-orange, #f97316);
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
  color: var(--vf-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.eyebrow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--vf-orange);
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.12);
}

.page-header h1 {
  margin: 0 0 5px;
  color: var(--vf-dark);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.page-header p {
  margin: 0;
  color: var(--vf-muted);
  font-size: 13px;
}

.primary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 16px;
  color: #ffffff;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
  border: 1px solid transparent;
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 2px 5px rgba(239, 68, 68, 0.16);
  cursor: pointer;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.primary-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 5px 12px rgba(239, 68, 68, 0.22);
}

.button-icon {
  font-size: 18px;
  font-weight: 400;
  line-height: 1;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.content-card {
  margin-bottom: 20px;
  overflow: hidden;
  background: var(--vf-surface, #ffffff);
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(24, 24, 27, 0.025);
}

.annotation-pool-toolbar {
  display: flex;
  gap: 10px;
  padding: 16px 22px;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
}

.pool-search,
.pool-filter {
  min-height: 34px;
  padding: 7px 10px;
  color: var(--vf-dark, #18181b);
  background: #ffffff;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 6px;
  font: inherit;
  font-size: 12px;
}

.pool-search {
  flex: 1;
  min-width: 180px;
}

.pool-filter {
  min-width: 150px;
}

.pool-message {
  padding: 20px 22px;
  color: #b91c1c;
  font-size: 12px;
}

.annotation-pool-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
}

.pool-table-wrapper {
  min-width: 0;
  overflow-x: auto;
}

.pool-table {
  min-width: 760px;
}

.pool-row {
  cursor: pointer;
}

.pool-row:focus,
.pool-row.selected {
  background: #fff7ed;
  outline: none;
}

.pool-status {
  display: inline-flex;
  padding: 5px 8px;
  border-radius: 999px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.pool-status-queued {
  color: #a16207;
  background: #fefce8;
}

.pool-status-in_progress {
  color: #c2410c;
  background: #fff7ed;
}

.pool-status-completed {
  color: #15803d;
  background: #f0fdf4;
}

.pool-status-no_samples {
  color: #71717a;
  background: #f4f4f5;
}

.pool-subtext {
  display: block;
  margin-top: 3px;
  color: var(--vf-muted, #71717a);
  font-size: 10px;
}

.pool-details {
  padding: 20px;
  border-left: 1px solid var(--vf-border-light, #f1f1f2);
  background: #fffdfb;
}

.pool-details-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.pool-details-header h3 {
  margin: 6px 0 0;
  color: var(--vf-dark, #18181b);
  font-size: 16px;
}

.close-details {
  width: 28px;
  height: 28px;
  color: var(--vf-muted, #71717a);
  background: transparent;
  border: 1px solid var(--vf-border, #e4e4e7);
  border-radius: 6px;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.pool-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin: 20px 0;
}

.pool-metrics div {
  padding: 10px;
  background: #ffffff;
  border: 1px solid var(--vf-border-light, #f1f1f2);
  border-radius: 6px;
}

.pool-metrics strong,
.pool-metrics span {
  display: block;
}

.pool-metrics strong {
  color: var(--vf-dark, #18181b);
  font-size: 16px;
}

.pool-metrics span {
  margin-top: 3px;
  color: var(--vf-muted, #71717a);
  font-size: 9px;
}

.pool-details h4 {
  margin: 0 0 10px;
  color: var(--vf-dark, #18181b);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.activity-list {
  max-height: 360px;
  padding: 0;
  margin: 0;
  overflow-y: auto;
  list-style: none;
}

.activity-list li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
}

.activity-list strong,
.activity-list span,
.activity-list time {
  display: block;
  font-size: 10px;
}

.activity-list strong {
  color: var(--vf-dark, #18181b);
}

.activity-list span,
.activity-list time {
  margin-top: 3px;
  color: var(--vf-muted, #71717a);
}

.activity-list time {
  flex-shrink: 0;
  text-align: right;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
}

.section-title-row {
  display: flex;
  align-items: center;
  gap: 9px;
}

.section-marker {
  width: 3px;
  height: 17px;
  border-radius: 4px;
  background: var(--vf-gradient, linear-gradient(135deg, #f97316, #ef4444));
}

.section-header h2 {
  margin: 0;
  color: var(--vf-dark, #18181b);
  font-size: 15px;
  font-weight: 700;
}

.section-header p {
  margin: 5px 0 0 12px;
  color: var(--vf-light-muted, #a1a1aa);
  font-size: 11px;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 26px 22px;
  font-size: 12px;
  color: var(--vf-muted, #71717a);
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--vf-orange);
  animation: pulse 1s ease-in-out infinite;
}

.dataset-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.dataset-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.dataset-table th {
  padding: 12px 22px;
  color: var(--vf-light-muted, #a1a1aa);
  background: #fafafa;
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-align: left;
  text-transform: uppercase;
}

.dataset-table td {
  padding: 15px 22px;
  color: var(--vf-dark, #18181b);
  border-bottom: 1px solid var(--vf-border-light, #f1f1f2);
  font-size: 12px;
  vertical-align: middle;
}

.dataset-table tbody tr:last-child td {
  border-bottom: none;
}

.dataset-table tbody tr {
  transition: background 0.15s ease;
}

.dataset-table tbody tr:hover {
  background: #fffaf7;
}

.dataset-name {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 180px;
}

.dataset-name strong {
  color: var(--vf-dark, #18181b);
  font-size: 12px;
  font-weight: 600;
}

.dataset-id {
  color: var(--vf-light-muted, #a1a1aa);
  font-size: 10px;
  font-weight: 500;
}

.participant-value {
  color: var(--vf-dark, #27272a);
  font-weight: 600;
}

.muted-value {
  color: var(--vf-light-muted, #a1a1aa);
}

.exercise-value {
  color: var(--vf-muted, #71717a);
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 11px;
}

.sample-count {
  color: var(--vf-dark, #18181b);
  font-weight: 600;
}

.labelled-count {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--vf-muted, #71717a);
  font-size: 11px;
}

.labelled-count strong {
  color: var(--vf-dark, #18181b);
  font-weight: 600;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 68px;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.status-badge.ready {
  color: #15803d;
  background: #f0fdf4;
}

.status-badge.processing {
  color: #c2410c;
  background: #fff7ed;
}

.status-badge.pending {
  color: #a16207;
  background: #fefce8;
}

.status-badge.failed {
  color: #dc2626;
  background: #fef2f2;
}

.empty-state {
  padding: 42px 24px;
  color: var(--vf-muted, #71717a);
  text-align: center;
  font-size: 12px;
}

.action-cell {
  display: flex;
  align-items: center;
  min-height: 30px;
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

.action-complete {
  color: #15803d;
  font-size: 10px;
  font-weight: 700;
}

.processing-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--vf-muted, #71717a);
  font-size: 10px;
  font-weight: 600;
}

.processing-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: processing-spin 0.8s linear infinite;
}

.retry-button {
  min-width: 48px;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.35;
  }

  50% {
    opacity: 1;
  }
}

@keyframes processing-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1000px) {
  .dataset-table {
    min-width: 820px;
  }
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 700px) {
  .dataset-page {
    padding: 20px;
  }
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 18px;
  }
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .page-actions {
    width: 100%;
    flex-direction: column;
  }

  .page-actions button {
    width: 100%;
  }

  .annotation-pool-toolbar {
    flex-direction: column;
  }

  .annotation-pool-layout {
    display: block;
  }

  .pool-details {
    border-top: 1px solid var(--vf-border-light, #f1f1f2);
    border-left: none;
  }
}
</style>
