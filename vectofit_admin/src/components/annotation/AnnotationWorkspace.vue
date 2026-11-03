<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDatasetAnnotation } from "../../hooks/useDatasetAnnotation";
import type {
  KneeAlignmentGrade,
  KneeDeviationDirection,
  SymmetryObservation,
} from "../../services/datasetAnnotationService";

const route = useRoute();
const router = useRouter();
const backTo = "/annotator/datasets";

const videoRef = ref<HTMLVideoElement | null>(null);
const playbackRate = ref(1);
const videoError = ref("");
const kneeSides = ["left", "right"] as const;
const kneeGrades: KneeAlignmentGrade[] = [
  "aligned",
  "borderline",
  "deviated",
  "unassessable",
];

function handleDirectionChange(side: "left" | "right", event: Event) {
  setKneeDirection(
    side,
    (event.target as HTMLSelectElement).value as KneeDeviationDirection,
  );
}

function handleSymmetryChange(event: Event) {
  setSymmetryObservation(
    (event.target as HTMLSelectElement).value as SymmetryObservation,
  );
}

function handleNotesInput(event: Event) {
  setNotes((event.target as HTMLTextAreaElement).value);
}

const {
  session,
  samples,
  currentSample,
  currentIndex,
  fps,
  annotation,
  targetLabel,
  labelledCount,
  isReviewComplete,
  currentSampleLabelState,
  isLoading,
  isSaving,
  error,
  load,
  setKneeGrade,
  setKneeDirection,
  setSymmetryObservation,
  setNotes,
  saveAndNext,
  clear,
  previous,
  next,
} = useDatasetAnnotation();

const activeVideo = computed(() => {
  const video = currentSample.value?.dataset_video;

  return video && typeof video === "object" ? video : null;
});

const activeVideoUrl = computed(
  () =>
    activeVideo.value?.video_url ?? session.value?.dataset.video_url ?? null,
);

const activeVideoLabel = computed(() => {
  const video = activeVideo.value;

  if (!video) {
    return "Dataset-level video";
  }

  const sourceLabel =
    video.source_label === true
      ? "GOOD FORM"
      : video.source_label === false
        ? "BAD FORM"
        : "UNKNOWN LABEL";

  return [
    video.participant_code ? `Participant ${video.participant_code}` : null,
    video.view_angle_name,
    `${sourceLabel}`,
  ]
    .filter(Boolean)
    .join(" · ");
});

const currentFps = computed(() => {
  const sampleFps = currentSample.value?.video_fps;

  return sampleFps != null && sampleFps > 0 ? sampleFps : fps.value;
});

const repStartTime = computed(() => {
  const startFrame = currentSample.value?.rep_assessment.start_frame;

  if (startFrame == null || currentFps.value <= 0) {
    return 0;
  }

  return startFrame / currentFps.value;
});

const repEndTime = computed(() => {
  const endFrame = currentSample.value?.rep_assessment.end_frame;

  if (endFrame == null || currentFps.value <= 0) {
    return null;
  }

  return endFrame / currentFps.value;
});

function seekToRep() {
  const video = videoRef.value;

  if (!video || video.readyState < HTMLMediaElement.HAVE_METADATA) {
    return;
  }

  video.currentTime = repStartTime.value;
}

function handleVideoLoadedMetadata() {
  const video = videoRef.value;

  if (!video) return;

  video.playbackRate = playbackRate.value;
  seekToRep();
}

function handleTimeUpdate() {
  const video = videoRef.value;

  if (
    !video ||
    repEndTime.value == null ||
    video.currentTime < repEndTime.value
  ) {
    return;
  }

  video.pause();
  seekToRep();
}

async function playRep() {
  const video = videoRef.value;

  if (!video || !activeVideoUrl.value) {
    return;
  }

  videoError.value = "";

  if (video.readyState < HTMLMediaElement.HAVE_METADATA) {
    videoError.value = "The source video is still loading.";
    return;
  }

  video.playbackRate = playbackRate.value;
  seekToRep();

  try {
    await video.play();
  } catch (playError) {
    console.error("Could not play the current repetition.", playError);
    videoError.value = "Could not play this video. Please try again.";
  }
}

watch(
  () => currentSample.value?.id,
  async () => {
    const video = videoRef.value;

    if (video) {
      video.pause();
      video.currentTime = 0;
    }

    videoError.value = "";

    await nextTick();
    seekToRep();
  },
);

watch(playbackRate, (rate) => {
  if (videoRef.value) {
    videoRef.value.playbackRate = rate;
  }
});

const handleSaveNext = async () => {
  const saved = await saveAndNext();

  if (!saved || isReviewComplete.value) {
    return;
  }

  await nextTick();
  seekToRep();
};

async function initialize(rawId: unknown) {
  const datasetId = Number(rawId);

  if (!Number.isInteger(datasetId) || datasetId <= 0) {
    await router.push(backTo);
    return;
  }

  await load(datasetId);
  await nextTick();
  seekToRep();

  requestAnimationFrame(seekToRep);
}

onMounted(async () => {
  await initialize(route.params.id);
});

watch(
  () => route.params.id,
  async (id) => {
    if (id !== undefined) {
      await initialize(id);
    }
  },
);
</script>

<template>
  <div class="annotation-page">
    <header class="annotation-header">
      <div>
        <div class="eyebrow">ANNOTATOR WORKSPACE</div>

        <h1>
          {{ session?.dataset.name }}
        </h1>

        <p>Frontal-plane bilateral knee alignment review.</p>
      </div>

      <button
        type="button"
        class="secondary-button"
        @click="router.push(backTo)"
      >
        Back to Datasets
      </button>
    </header>

    <div v-if="isLoading" class="loading">Loading annotation workspace...</div>

    <div v-else-if="error && !session" class="error">
      {{ error }}
    </div>

    <section
      v-else-if="session && isReviewComplete"
      class="annotation-card annotation-complete"
    >
      <h2>Manual Review Complete</h2>

      <p>All samples in this review queue have been manually annotated.</p>

      <div class="completion-count">
        <strong>{{ labelledCount }} / {{ samples.length }}</strong>
        <span>Samples reviewed</span>
      </div>

      <p class="completion-note">
        Your annotations have been saved.
      </p>

      <button
        type="button"
        class="primary-button"
        @click="router.push(backTo)"
      >
        Return to Datasets
      </button>
    </section>

    <section
      v-else-if="session && samples.length === 0"
      class="annotation-card annotation-complete"
    >
      <h2>No Repetitions to Review</h2>

      <p>This dataset does not contain any samples available for annotation.</p>

      <button
        type="button"
        class="primary-button"
        @click="router.push(backTo)"
      >
        Return to Datasets
      </button>
    </section>

    <template v-else-if="session && currentSample">
      <p v-if="error" class="inline-error" role="alert">
        {{ error }}
      </p>

      <section class="annotation-card annotation-meta">
        <div>
          <span>Annotator</span>
          <strong>{{ session.annotator_name }}</strong>
        </div>

        <div>
          <span>Progress</span>
          <strong>{{ currentIndex + 1 }} / {{ samples.length }}</strong>
        </div>

        <div>
          <span>Manually Reviewed</span>
          <strong>{{ labelledCount }} / {{ samples.length }}</strong>
        </div>
      </section>

      <main class="annotation-workspace">
        <section class="annotation-card video-panel">
          <div class="video-source-meta">
            <span>Current video: </span>

            <strong>{{ activeVideoLabel }}</strong>
          </div>

          <video
            v-if="activeVideoUrl"
            :key="activeVideoUrl"
            ref="videoRef"
            :src="activeVideoUrl"
            controls
            playsinline
            @loadedmetadata="handleVideoLoadedMetadata"
            @timeupdate="handleTimeUpdate"
          ></video>

          <div v-else class="video-unavailable">
            <strong>Source video unavailable</strong>
            <p>
              This repetition does not have a playable video URL. Check the
              imported video's processing status.
            </p>
          </div>

          <p v-if="videoError" class="video-error">
            {{ videoError }}
          </p>

          <div class="video-controls">
            <button
              type="button"
              :disabled="currentIndex === 0"
              @click="previous"
            >
              Previous
            </button>

            <button type="button" :disabled="!activeVideoUrl" @click="playRep">
              Play Rep
            </button>

            <button
              type="button"
              :disabled="currentIndex >= samples.length - 1"
              @click="next"
            >
              Next
            </button>

            <select v-model.number="playbackRate">
              <option :value="0.5">0.5×</option>
              <option :value="0.75">0.75×</option>
              <option :value="1">1×</option>
              <option :value="1.5">1.5×</option>
              <option :value="2">2×</option>
            </select>
          </div>
        </section>

        <section class="annotation-card criteria-panel">
          <div class="panel-heading">
            <div>
              <span>Rep {{ currentSample.rep_assessment.rep_number }}</span>
              <h2>Knee Alignment</h2>
              <p
                v-if="currentSampleLabelState"
                class="annotation-state"
                :class="`state-${currentSampleLabelState}`"
              >
                {{
                  currentSampleLabelState === "manual"
                    ? "Manually reviewed"
                    : currentSampleLabelState === "inherited"
                      ? "Inherited ZIP label — review needed"
                      : "Unreviewed"
                }}
              </p>
            </div>

            <span
              :class="['verdict', (targetLabel ?? 'pending').toLowerCase()]"
            >
              {{ targetLabel?.toUpperCase() ?? "PENDING" }}
            </span>
          </div>

          <div class="criteria-list">
            <div v-for="side in kneeSides" :key="side" class="criterion">
              <strong :id="`${side}-knee-label`">{{
                side === "left" ? "Left knee" : "Right knee"
              }}</strong>
              <div class="criterion-actions">
                <button
                  v-for="grade in kneeGrades"
                  :key="grade"
                  type="button"
                  :class="{ active: annotation[side].grade === grade }"
                  @click="setKneeGrade(side, grade)"
                >
                  {{ grade }}
                </button>
              </div>
              <label class="direction-field" :for="`${side}-direction`">
                <span :id="`${side}-direction-label`">Deviation direction</span>
                <select
                  :id="`${side}-direction`"
                  class="direction-select"
                  :aria-labelledby="`${side}-knee-label ${side}-direction-label`"
                  :value="annotation[side].direction ?? 'uncertain'"
                  :disabled="
                    annotation[side].grade === null ||
                    annotation[side].grade === 'unassessable' ||
                    annotation[side].grade === 'aligned'
                  "
                  @change="handleDirectionChange(side, $event)"
                >
                  <option value="uncertain">Direction uncertain</option>
                  <option value="valgus">Valgus</option>
                  <option value="varus">Varus</option>
                </select>
              </label>
            </div>
          </div>

          <label class="annotation-field">
            <span class="field-label">Symmetry observation</span>
            <span class="field-hint"
              >Compare the knees during this repetition.</span
            >
            <select
              class="annotation-control"
              :value="annotation.symmetry_observation"
              @change="handleSymmetryChange"
            >
              <option value="not_recorded">Not recorded</option>
              <option value="symmetric">Symmetric</option>
              <option value="asymmetric">Asymmetric</option>
              <option value="uncertain">Uncertain</option>
            </select>
          </label>
          <label class="annotation-field notes-field">
            <span class="field-label">Notes</span>
            <span class="field-hint"
              >Add details that support your assessment.</span
            >
            <textarea
              class="annotation-control"
              :value="annotation.notes"
              rows="4"
              placeholder="Describe any visible alignment or review details…"
              @input="handleNotesInput"
            />
          </label>

          <div class="annotation-actions">
            <button
              type="button"
              class="secondary-button"
              :disabled="isSaving"
              @click="clear"
            >
              Clear
            </button>

            <button
              type="button"
              class="primary-button"
              :disabled="isSaving || targetLabel === null"
              @click="handleSaveNext"
            >
              {{ isSaving ? "Saving..." : "Save & Next" }}
            </button>
          </div>
        </section>
      </main>
    </template>
  </div>
</template>

<style scoped>
.annotation-page {
  width: 100%;
  min-height: 100%;
  padding: 28px 32px 40px;
  box-sizing: border-box;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

.annotation-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.annotation-header > div {
  min-width: 0;
}

.annotation-meta {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.annotation-state {
  margin: 8px 0 0;
  font-size: 11px;
  font-weight: 650;
}

.annotation-complete {
  max-width: 640px;
  margin: 40px auto;
  padding: 32px;
  text-align: center;
}

.annotation-complete h2 {
  margin-bottom: 12px;
}

.annotation-complete p {
  color: #667085;
  line-height: 1.6;
}

.completion-count {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 24px 0;
}

.completion-count strong {
  font-size: 28px;
  color: #15803d;
}

.completion-count span {
  color: #667085;
  font-size: 13px;
}

.completion-note {
  margin-bottom: 24px;
}

.state-manual {
  color: #047857;
}

.state-inherited {
  color: #b45309;
}

.state-unlabeled {
  color: #64748b;
}

@media (max-width: 700px) {
  .annotation-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  margin-bottom: 7px;
  color: #f97316;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.annotation-header h1 {
  margin: 0;
  color: #172033;
  font-size: 27px;
  line-height: 1.2;
  font-weight: 750;
  letter-spacing: -0.02em;
}

.annotation-header p {
  max-width: 720px;
  margin: 7px 0 0;
  color: #718096;
  font-size: 13px;
  line-height: 1.55;
}

.annotation-card {
  background: #ffffff;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  box-shadow: 0 5px 18px rgba(15, 23, 42, 0.045);
}

.annotation-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-bottom: 20px;
  overflow: hidden;
}

.annotation-meta > div {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 16px 20px;
}

.annotation-meta > div + div {
  border-left: 1px solid #edf1f5;
}

.annotation-meta span {
  color: #8a96a8;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.annotation-meta strong {
  color: #172033;
  font-size: 17px;
  font-weight: 750;
}

.annotation-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(350px, 0.8fr);
  align-items: start;
  gap: 20px;
}

.video-panel {
  overflow: hidden;
}

.video-source-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  min-height: 82px;
  padding: 16px 20px;
  box-sizing: border-box;
  border-bottom: 1px solid #e8edf3;
  background: #ffffff;
}

.video-source-meta > span {
  color: #8a96a8;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.video-source-meta > strong {
  display: block;
  max-width: 100%;
  color: #344054;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.5;
  white-space: normal;
  overflow-wrap: anywhere;
}

.video-panel video {
  display: block;
  width: 100%;
  max-height: 620px;
  min-height: 420px;
  object-fit: contain;
  background: #10151f;
}

.video-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 13px 14px;
  border-top: 1px solid #e8edf3;
  background: #ffffff;
}

.video-controls button,
.video-controls select {
  height: 36px;
  border: 1px solid #dce3eb;
  border-radius: 8px;
  background: #ffffff;
  color: #344054;
  font-family: inherit;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease;
}

.video-controls button {
  padding: 0 13px;
}

.video-controls button:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.video-controls select {
  margin-left: auto;
  padding: 0 30px 0 10px;
  cursor: pointer;
}

.criteria-panel {
  padding: 22px;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 15px;
  margin-bottom: 20px;
}

.panel-heading > div > span {
  display: block;
  margin-bottom: 4px;
  color: #8a96a8;
  font-size: 11px;
  font-weight: 650;
}

.panel-heading h2 {
  margin: 0;
  color: #172033;
  font-size: 18px;
  font-weight: 750;
}

.verdict {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.verdict.pass {
  background: #ecfdf3;
  color: #047857;
}

.verdict.fail {
  background: #fff1f2;
  color: #be123c;
}

.verdict.pending {
  background: #f1f5f9;
  color: #64748b;
}

.criteria-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.criterion {
  display: flex;
  align-items: stretch;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  padding: 14px;
  border: 1px solid #e8edf3;
  border-radius: 10px;
  background: #fbfcfe;
}

.criterion > div:first-child {
  min-width: 0;
}

.criterion strong {
  color: #344054;
  font-size: 13px;
  font-weight: 650;
}

.criterion-actions {
  display: flex;
  gap: 6px;
  width: 100%;
  min-width: 0;
}

.criterion-actions button {
  flex: 1 1 0;
  min-width: 0;
  min-height: 34px;
  padding: 4px 5px;
  border: 1px solid #dce3eb;
  border-radius: 7px;
  background: #ffffff;
  color: #667085;
  font-family: inherit;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease,
    transform 0.1s ease;
}

.criterion-actions button:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.criterion-actions button:active {
  transform: translateY(1px);
}

.criterion-actions button.active:first-child {
  border-color: #10b981;
  background: #ecfdf3;
  color: #047857;
}

.criterion-actions button.active:last-child {
  border-color: #f43f5e;
  background: #fff1f2;
  color: #be123c;
}

.annotation-field,
.direction-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 18px;
}

.direction-field {
  width: 100%;
  min-width: 0;
  margin-top: 0;
}

.field-label,
.direction-field > span {
  color: #475467;
  font-size: 12px;
  font-weight: 700;
}

.field-hint {
  color: #8a96a8;
  font-size: 11px;
  line-height: 1.4;
}

.annotation-control,
.direction-select {
  width: 100%;
  min-height: 42px;
  padding: 10px 12px;
  box-sizing: border-box;
  border: 1px solid #dce3eb;
  border-radius: 9px;
  outline: none;
  background: #ffffff;
  color: #344054;
  font-family: inherit;
  font-size: 13px;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.annotation-control::placeholder {
  color: #a0a9b7;
}

.annotation-control:focus-visible,
.direction-select:focus-visible {
  border-color: #f97316;
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1);
}

.annotation-control:not(textarea),
.direction-select {
  cursor: pointer;
}

.notes-field {
  margin-top: 16px;
}

.notes-field textarea {
  min-height: 104px;
  resize: vertical;
  line-height: 1.5;
}

.annotation-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid #edf1f5;
}

.primary-button,
.secondary-button {
  height: 38px;
  padding: 0 15px;
  border-radius: 8px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.1s ease;
}

.primary-button {
  border: 1px solid #f97316;
  background: #f97316;
  color: #ffffff;
}

.primary-button:hover:not(:disabled) {
  background: #ea580c;
  border-color: #ea580c;
}

.secondary-button {
  border: 1px solid #dce3eb;
  background: #ffffff;
  color: #475467;
}

.secondary-button:hover:not(:disabled) {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.primary-button:active:not(:disabled),
.secondary-button:active:not(:disabled) {
  transform: translateY(1px);
}

.primary-button:disabled,
.secondary-button:disabled,
.criterion-actions button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.loading,
.error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 260px;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  background: #ffffff;
  color: #667085;
  font-size: 13px;
}

.error {
  color: #be123c;
  background: #fff8f8;
  border-color: #fecdd3;
}

.inline-error {
  margin: 0 0 16px;
  padding: 12px 16px;
  border: 1px solid #fecdd3;
  border-radius: 10px;
  background: #fff8f8;
  color: #be123c;
  font-size: 13px;
  line-height: 1.5;
}

@media (max-width: 1100px) {
  .annotation-workspace {
    grid-template-columns: 1fr;
  }

  .video-panel video {
    max-height: 560px;
  }

  .criteria-panel {
    width: 100%;
    box-sizing: border-box;
  }
}

@media (max-width: 700px) {
  .annotation-page {
    padding: 20px 16px 30px;
  }

  .annotation-header {
    flex-direction: column;
  }

  .annotation-header .secondary-button {
    width: 100%;
  }

  .annotation-meta {
    grid-template-columns: 1fr;
  }

  .annotation-meta > div + div {
    border-top: 1px solid #edf1f5;
    border-left: none;
  }

  .video-panel video {
    min-height: 260px;
  }

  .video-controls {
    flex-wrap: wrap;
  }

  .video-controls select {
    margin-left: 0;
  }

  .video-source-meta {
    min-height: 76px;
    padding: 14px 16px;
  }

  .video-source-meta > span {
    font-size: 9px;
  }

  .video-source-meta > strong {
    font-size: 13px;
  }

  .source-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 3px;
  }

  .source-chip {
    display: inline-flex;
    align-items: center;
    padding: 6px 9px;
    border: 1px solid transparent;
    border-radius: 7px;
    font-size: 11px;
    font-weight: 750;
  }

  .source-chip.angle {
    background: #eff6ff;
    color: #1d4ed8;
  }

  .source-chip.good {
    background: #ecfdf3;
    border-color: #a7f3d0;
    color: #047857;
  }

  .source-chip.bad {
    background: #fff1f2;
    border-color: #fecdd3;
    color: #be123c;
  }

  .source-chip.unknown {
    background: #f1f5f9;
    color: #475569;
  }

  .source-chip.review {
    background: #fffbeb;
    color: #92400e;
  }

  .source-label-note {
    margin: 0;
    color: #667085;
    font-size: 11px;
    line-height: 1.5;
  }
  .video-unavailable {
    display: flex;
    min-height: 260px;
    padding: 24px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: #10151f;
    color: #ffffff;
    text-align: center;
  }

  .video-unavailable p {
    max-width: 360px;
    margin: 0;
    color: #cbd5e1;
    font-size: 12px;
    line-height: 1.6;
  }

  .video-error {
    margin: 0;
    padding: 10px 14px;
    background: #fff1f2;
    color: #be123c;
    font-size: 12px;
  }

  .criterion {
    align-items: stretch;
    padding: 14px;
  }

  .criterion-actions {
    width: 100%;
  }

  .criterion-actions button {
    flex: 1;
  }

  .annotation-actions {
    flex-direction: column-reverse;
  }

  .annotation-actions button {
    width: 100%;
  }
}
</style>
