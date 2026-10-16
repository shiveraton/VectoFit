<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDatasetAnnotation } from "../../hooks/useDatasetAnnotation";

const route = useRoute();
const router = useRouter();

const videoRef = ref<HTMLVideoElement | null>(null);
const playbackRate = ref(1);

const {
  session,
  samples,
  currentSample,
  currentIndex,
  fps,
  criteria,
  errorLabel,
  verdict,
  labelledCount,
  isLoading,
  isSaving,
  error,
  load,
  setCriterion,
  saveAndNext,
  clear,
  previous,
  next,
} = useDatasetAnnotation();

const repStartTime = computed(() => {
  if (!currentSample.value?.rep_assessment.start_frame || !fps.value) {
    return 0;
  }

  return currentSample.value.rep_assessment.start_frame / fps.value;
});

const repEndTime = computed(() => {
  if (currentSample.value?.rep_assessment.end_frame == null || !fps.value) {
    return null;
  }

  return currentSample.value.rep_assessment.end_frame / fps.value;
});

const seekToRep = () => {
  if (!videoRef.value) return;

  videoRef.value.currentTime = repStartTime.value;
};

const handleTimeUpdate = () => {
  if (
    videoRef.value &&
    repEndTime.value !== null &&
    videoRef.value.currentTime >= repEndTime.value
  ) {
    videoRef.value.pause();
    videoRef.value.currentTime = repStartTime.value;
  }
};

const playRep = async () => {
  if (!videoRef.value) return;

  videoRef.value.playbackRate = playbackRate.value;
  seekToRep();
  await videoRef.value.play();
};

const handleSaveNext = async () => {
  await saveAndNext();
  seekToRep();
};

onMounted(async () => {
  const datasetId = Number(route.params.id);

  if (!Number.isInteger(datasetId)) {
    router.push("/dataset");
    return;
  }

  await load(datasetId);

  requestAnimationFrame(seekToRep);
});
</script>

<template>
  <div class="annotation-page">
    <header class="annotation-header">
      <div>
        <div class="eyebrow">DATASET ANNOTATION</div>

        <h1>
          {{ session?.dataset.name }}
        </h1>

        <p>
          Rep-by-rep ground-truth annotation based on the VectoFit squat quality
          rubric.
        </p>
      </div>

      <button
        type="button"
        class="secondary-button"
        @click="router.push('/dataset')"
      >
        Back to Datasets
      </button>
    </header>

    <div v-if="isLoading" class="loading">Loading annotation workspace...</div>

    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <template v-else-if="session && currentSample">
      <section class="annotation-card annotation-meta">
        <div>
          <span>Progress</span>
          <strong> {{ currentIndex + 1 }} / {{ samples.length }} </strong>
        </div>

        <div>
          <span>Labelled</span>
          <strong> {{ labelledCount }} / {{ samples.length }} </strong>
        </div>

        <div>
          <span>Current Rep</span>
          <strong> Rep {{ currentSample.rep_assessment.rep_number }} </strong>
        </div>
      </section>

      <main class="annotation-workspace">
        <section class="annotation-card video-panel">
          <video
            ref="videoRef"
            :src="session.dataset.video_url ?? undefined"
            controls
            playsinline
            @timeupdate="handleTimeUpdate"
          ></video>

          <div class="video-controls">
            <button type="button" @click="previous">Previous</button>

            <button type="button" @click="playRep">Play Rep</button>

            <button type="button" @click="next">Next</button>

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
              <h2>Movement Quality</h2>
            </div>

            <span :class="['verdict', verdict.toLowerCase()]">
              {{ verdict }}
            </span>
          </div>

          <div class="criteria-list">
            <div
              v-for="criterion in [
                ['depth', 'Depth'],
                ['knee', 'Knee'],
                ['trunk', 'Trunk'],
                ['symmetry', 'Symmetry'],
                ['foot', 'Foot'],
                ['completion', 'Completion'],
              ]"
              :key="criterion[0]"
              class="criterion"
            >
              <div>
                <strong>{{ criterion[1] }}</strong>
              </div>

              <div class="criterion-actions">
                <button
                  type="button"
                  :class="{
                    active: criteria[criterion[0]] === true,
                  }"
                  @click="setCriterion(criterion[0] as any, true)"
                >
                  Pass
                </button>

                <button
                  type="button"
                  :class="{
                    active: criteria[criterion[0]] === false,
                  }"
                  @click="setCriterion(criterion[0] as any, false)"
                >
                  Fail
                </button>
              </div>
            </div>
          </div>

          <label class="error-label-field">
            <span>Error Labels</span>
            <input
              v-model="errorLabel"
              type="text"
              placeholder="knee_valgus,foot_instability"
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
              :disabled="isSaving || verdict === 'PENDING'"
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
  border-top: 1px solid #edf1f5;
}

.criterion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 58px;
  border-bottom: 1px solid #edf1f5;
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
  flex-shrink: 0;
}

.criterion-actions button {
  min-width: 58px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid #dce3eb;
  border-radius: 7px;
  background: #ffffff;
  color: #667085;
  font-family: inherit;
  font-size: 11px;
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

.error-label-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 18px;
}

.error-label-field span {
  color: #475467;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.error-label-field input {
  width: 100%;
  height: 38px;
  padding: 0 11px;
  box-sizing: border-box;
  border: 1px solid #dce3eb;
  border-radius: 8px;
  outline: none;
  background: #ffffff;
  color: #344054;
  font-family: inherit;
  font-size: 12px;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.error-label-field input::placeholder {
  color: #a0a9b7;
}

.error-label-field input:focus {
  border-color: #f97316;
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1);
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

  .criterion {
    align-items: flex-start;
    flex-direction: column;
    justify-content: center;
    padding: 12px 0;
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
