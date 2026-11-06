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
const datasetHome = import.meta.env.MODE === "public" ? "/annotator" : "/dataset";

const videoRef = ref<HTMLVideoElement | null>(null);
const playbackRate = ref(1);
const videoError = ref("");
const reviewingCompleted = ref(false);
const kneeSides = ["left", "right"] as const;
const kneeGrades: KneeAlignmentGrade[] = [
  "aligned", "borderline", "deviated", "unassessable",
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
  pendingReviewCount,
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

  if (import.meta.env.MODE === "public") {
    return [video.participant_code, video.view_angle_name].filter(Boolean).join(" / ");
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
    videoRef.value?.pause();
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

onMounted(async () => {
  const datasetId = Number(route.params.id);

  if (!Number.isInteger(datasetId) || datasetId <= 0) {
    await router.push(datasetHome);
    return;
  }

  await load(datasetId);
  await nextTick();
  seekToRep();

  requestAnimationFrame(seekToRep);
});
</script>

<template>
  <div class="annotation-page">
    <header class="page-header">
      <div>
    <div class="eyebrow">DATASET ANNOTATION</div>

        <h1>
          {{ session?.dataset.name }}
        </h1>

        <p>
          Frontal-plane bilateral knee alignment review.
        </p>
      </div>

      <button
        type="button"
        class="secondary-button"
        :disabled="isSaving"
        @click="router.push(datasetHome)"
      >
        Back to Datasets
      </button>
    </header>

    <div v-if="isLoading" class="loading" role="status">Loading annotation workspace...</div>

    <div v-if="error" class="error" role="alert">
      {{ error }}
    </div>

    <section
      v-if="!isLoading && session && isReviewComplete && !reviewingCompleted"
      class="annotation-card annotation-complete"
    >
      <h2>Manual Review Complete</h2>

      <p>All samples in this review queue have been manually annotated.</p>

      <div class="completion-count">
        <strong>{{ labelledCount }} / {{ samples.length }}</strong>
        <span>Samples reviewed</span>
      </div>

      <p class="completion-note">
        All of your ratings have been saved and confirmed.
      </p>

      <button
        type="button"
        class="primary-button"
        @click="router.push(datasetHome)"
      >
        Return to Datasets
      </button>
      <button type="button" class="secondary-button" @click="reviewingCompleted = true">
        Review saved ratings
      </button>
    </section>

    <template v-else-if="!isLoading && session && currentSample">
      <section class="annotation-card annotation-meta">
        <div>
          <span>Progress</span>
          <strong>{{ currentIndex + 1 }} / {{ samples.length }}</strong>
        </div>

        <div>
          <span>Manually Reviewed</span>
          <strong>{{ labelledCount }} / {{ samples.length }}</strong>
        </div>

        <div>
          <span>Awaiting Review</span>
          <strong>{{ pendingReviewCount }}</strong>
        </div>
      </section>

      <div class="annotation-workspace">
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
              :disabled="isSaving || currentIndex === 0"
              @click="previous"
            >
              Previous
            </button>

            <button type="button" :disabled="!activeVideoUrl" @click="playRep">
              Play Rep
            </button>

            <button
              type="button"
              :disabled="isSaving || currentIndex >= samples.length - 1"
              @click="next"
            >
              Next
            </button>

            <select v-model.number="playbackRate" aria-label="Playback speed">
              <option :value="0.5">0.5×</option>
              <option :value="0.75">0.75×</option>
              <option :value="1">1×</option>
              <option :value="1.5">1.5×</option>
              <option :value="2">2×</option>
            </select>
          </div>
        </section>

        <section class="annotation-card criteria-panel">
          <fieldset :disabled="isSaving" class="annotation-fields" aria-label="Knee assessment">
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

          <span :class="['verdict', (targetLabel ?? 'pending').toLowerCase()]">
            {{ targetLabel?.toUpperCase() ?? 'PENDING' }}
            </span>
          </div>

          <div class="criteria-list">
            <div v-for="side in kneeSides" :key="side" class="criterion">
              <strong>{{ side === 'left' ? 'Left knee' : 'Right knee' }}</strong>
              <div class="criterion-actions">
                <button v-for="grade in kneeGrades" :key="grade"
                  type="button" :class="{ active: annotation[side].grade === grade }"
                  :aria-pressed="annotation[side].grade === grade" :aria-label="`${side} knee: ${grade}`"
                  @click="setKneeGrade(side, grade)">{{ grade }}</button>
              </div>
              <select :aria-label="`${side} knee deviation direction`" :value="annotation[side].direction ?? ''" :disabled="annotation[side].grade === null || annotation[side].grade === 'unassessable' || annotation[side].grade === 'aligned'"
                @change="handleDirectionChange(side, $event)">
                <option value="uncertain">Direction uncertain</option>
                <option value="valgus">Valgus</option>
                <option value="varus">Varus</option>
              </select>
            </div>
          </div>

          <label class="error-label-field"><span>Symmetry observation</span>
            <select :value="annotation.symmetry_observation" @change="handleSymmetryChange">
              <option value="not_recorded">Not recorded</option><option value="symmetric">Symmetric</option>
              <option value="asymmetric">Asymmetric</option><option value="uncertain">Uncertain</option>
            </select>
          </label>
          <label class="error-label-field"><span>Notes</span>
            <textarea :value="annotation.notes" rows="3" @input="handleNotesInput" />
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
          </fieldset>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.annotation-fields { margin: 0; padding: 0; border: 0; min-width: 0; }
.annotation-card { min-width: 0; background: var(--vf-surface); border: 1px solid var(--vf-border); border-radius: 8px; }
.annotation-meta { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 24px; overflow: hidden; }
.annotation-meta > div { display: flex; flex-direction: column; gap: 8px; padding: 20px 24px; }
.annotation-meta > div + div { border-left: 1px solid var(--vf-border); }
.annotation-meta span { color: var(--vf-muted); font-size: 12px; }
.annotation-meta strong { color: var(--vf-dark); font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }
.annotation-workspace { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr); gap: 24px; align-items: start; }
.video-panel { overflow: hidden; }
.video-source-meta { display: flex; flex-direction: column; gap: 4px; padding: 16px 20px; }
.video-source-meta span { color: var(--vf-muted); font-size: 12px; }
.video-source-meta strong { font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.video-panel video { display: block; width: 100%; max-height: 620px; min-height: 320px; object-fit: contain; background: #10151f; }
.video-unavailable { display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 8px; min-height: 320px; padding: 24px; background: #10151f; color: white; text-align: center; }
.video-unavailable p { max-width: 360px; margin: 0; font-size: 13px; color: #cbd5e1; line-height: 1.6; overflow-wrap: anywhere; }
.video-error { margin: 0; padding: 12px 16px; color: var(--vf-red); background: var(--vf-red-soft); }
.video-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--vf-border); }
.video-controls button, .video-controls select { min-height: 40px; padding: 8px 12px; border: 1px solid var(--vf-control-border); border-radius: 8px; background: white; color: var(--vf-text); font-size: 12px; }
.video-controls button { cursor: pointer; }
.video-controls button:hover:not(:disabled) { background: #f4f4f5; }
.video-controls select { margin-left: auto; }
.criteria-panel { padding: 24px; }
.panel-heading { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 24px; }
.panel-heading > div { min-width: 0; }
.panel-heading > div > span { color: var(--vf-muted); font-size: 12px; }
.panel-heading h2 { margin: 4px 0; font-size: 18px; font-weight: 600; }
.annotation-state { margin: 8px 0 0; font-size: 12px; color: var(--vf-muted); }
.state-manual { color: var(--vf-success); }
.state-inherited { color: var(--vf-warning); }
.verdict { padding: 4px 8px; border-radius: 4px; background: #f4f4f5; color: var(--vf-muted); font-size: 11px; font-weight: 600; }
.verdict.good { background: var(--vf-success-soft); color: var(--vf-success); }
.verdict.bad { background: var(--vf-red-soft); color: var(--vf-red); }
.verdict.borderline, .verdict.unassessable { background: var(--vf-warning-soft); color: var(--vf-warning); }
.criterion { display: flex; flex-direction: column; gap: 12px; padding: 20px 0; border-top: 1px solid var(--vf-border); }
.criterion strong { font-size: 14px; font-weight: 600; }
.criterion-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.criterion-actions button { min-width: 0; min-height: 40px; padding: 8px; border: 1px solid var(--vf-control-border); border-radius: 6px; background: #fff; color: var(--vf-text); font-size: 12px; cursor: pointer; }
.criterion-actions button:hover { background: #f4f4f5; }
.criterion-actions button.active { background: var(--vf-orange-soft); color: var(--vf-orange-dark); border-color: var(--vf-orange); font-weight: 600; }
.criterion select, .error-label-field select, .error-label-field textarea { width: 100%; padding: 8px 12px; color: var(--vf-text); border: 1px solid var(--vf-control-border); background: #fff; border-radius: 8px; }
.error-label-field { display: flex; flex-direction: column; gap: 8px; margin-top: 20px; font-size: 13px; }
.error-label-field textarea { resize: vertical; }
.annotation-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--vf-border); }
.annotation-complete { max-width: 640px; margin: 40px auto; padding: 32px; }
.annotation-complete h2 { margin: 0 0 12px; font-size: 20px; }
.annotation-complete p { color: var(--vf-muted); }
.completion-count { display: flex; flex-direction: column; gap: 4px; margin: 24px 0; }
.completion-count strong { font-size: 28px; color: var(--vf-success); }
.completion-count span { color: var(--vf-muted); font-size: 12px; }
.loading, .error { padding: 24px; border: 1px solid var(--vf-border); border-radius: 8px; background: #fff; color: var(--vf-muted); }
.error { color: var(--vf-red); background: var(--vf-red-soft); border-color: #fecaca; }
@media (max-width: 1200px) { .annotation-workspace { grid-template-columns: 1fr; } }
@media (max-width: 600px) {
  .annotation-meta > div { padding: 16px 12px; }
  .annotation-meta strong { font-size: 18px; }
  .criteria-panel { padding: 20px 16px; }
  .video-controls select { margin-left: 0; }
  .video-panel video, .video-unavailable { min-height: 260px; }
  .annotation-actions > button { flex: 1; }
}
</style>
