import { computed, ref } from "vue";
import {
  datasetAnnotationService,
  annotationRequestError,
  emptyKneeAnnotation,
  type DatasetSample,
  type AnnotationSession,
  type KneeAnnotation,
  type KneeAlignmentGrade,
  type KneeDeviationDirection,
  type SymmetryObservation,
  type TargetLabel,
} from "../services/datasetAnnotationService";

type SampleAnnotationState = "manual" | "inherited" | "unlabeled";

function isManuallyAnnotated(sample: DatasetSample): boolean {
  return sample.knee_annotation != null;
}

function deriveTargetLabel(annotation: KneeAnnotation): TargetLabel | null {
  const left = annotation.left.grade;
  const right = annotation.right.grade;

  if (left === null || right === null) {
    return null;
  }

  if (left === "deviated" || right === "deviated") {
    return "bad";
  }

  if (left === "unassessable" || right === "unassessable") {
    return "unassessable";
  }

  if (left === "borderline" || right === "borderline") {
    return "borderline";
  }

  return "good";
}

function mergeSavedSample(
  original: DatasetSample,
  saved: DatasetSample,
): DatasetSample {
  const savedVideo = saved.dataset_video;

  const datasetVideo =
    savedVideo !== null && typeof savedVideo === "object"
      ? savedVideo
      : original.dataset_video;

  return {
    ...original,
    ...saved,
    dataset_video: datasetVideo,
    video_fps: saved.video_fps ?? original.video_fps ?? null,
  };
}

export function useDatasetAnnotation() {
  const session = ref<AnnotationSession | null>(null);
  const currentIndex = ref(0);
  const annotation = ref<KneeAnnotation>(emptyKneeAnnotation());

  const isLoading = ref(false);
  const isSaving = ref(false);
  const error = ref<string | null>(null);

  const currentSample = computed<DatasetSample | null>(
    () => session.value?.samples[currentIndex.value] ?? null,
  );

  const samples = computed(() => session.value?.samples ?? []);
  const fps = computed(() => session.value?.fps ?? 0);

  const targetLabel = computed<TargetLabel | null>(() =>
    deriveTargetLabel(annotation.value),
  );

  const currentSampleLabelState = computed<SampleAnnotationState | null>(() => {
    const sample = currentSample.value;

    if (!sample) return null;
    if (isManuallyAnnotated(sample)) return "manual";

    if (sample.is_correct != null) return "inherited";

    return "unlabeled";
  });

  const labelledCount = computed(
    () => samples.value.filter(isManuallyAnnotated).length,
  );

  const inheritedLabelCount = computed(
    () =>
      samples.value.filter(
        (sample) => !isManuallyAnnotated(sample) && sample.is_correct != null,
      ).length,
  );

  const pendingReviewCount = computed(
    () => samples.value.length - labelledCount.value,
  );

  const isReviewComplete = computed(
    () => samples.value.length > 0 && pendingReviewCount.value === 0,
  );

  const loadCurrentSample = () => {
    const sample = currentSample.value;

    annotation.value =
      sample?.knee_annotation != null
        ? JSON.parse(JSON.stringify(sample.knee_annotation))
        : emptyKneeAnnotation();
  };

  const load = async (datasetId: number) => {
    isLoading.value = true;
    error.value = null;

    try {
      session.value = await datasetAnnotationService.getSession(datasetId);
      currentIndex.value = Math.max(0, session.value.samples.findIndex(sample => sample.knee_annotation == null));
      loadCurrentSample();
    } catch (err) {
      console.error(err);
      error.value = "Unable to load annotation data.";
    } finally {
      isLoading.value = false;
    }
  };

  const setKneeGrade = (
    side: "left" | "right",
    grade: KneeAlignmentGrade | null,
  ) => {
    annotation.value[side].grade = grade;

    if (grade === null || grade === "unassessable") {
      annotation.value[side].direction = null;
    } else if (grade === "aligned") {
      annotation.value[side].direction = "none";
    } else if (
      annotation.value[side].direction === null ||
      annotation.value[side].direction === "none"
    ) {
      annotation.value[side].direction = "uncertain";
    }
  };

  const setKneeDirection = (
    side: "left" | "right",
    direction: KneeDeviationDirection,
  ) => {
    annotation.value[side].direction = direction;
  };

  const setSymmetryObservation = (value: SymmetryObservation) => {
    annotation.value.symmetry_observation = value;
  };

  const setNotes = (value: string) => {
    annotation.value.notes = value;
  };

  const save = async (): Promise<boolean> => {
    const sample = currentSample.value;

    if (isSaving.value) return false;
    if (!sample || targetLabel.value === null) {
      error.value = "Assess both knees before saving.";
      return false;
    }

    isSaving.value = true;
    error.value = null;

    try {
      const payload: KneeAnnotation = JSON.parse(JSON.stringify(annotation.value));
      const saved = await datasetAnnotationService.save(sample.id, {
        knee_annotation: payload,
      });

      if (session.value) {
        session.value.samples[currentIndex.value] = mergeSavedSample(sample, {
          ...saved,
          knee_annotation: saved.knee_annotation ?? payload,
          target_label: saved.target_label ?? targetLabel.value,
        });
      }

      return true;
    } catch (err) {
      console.error(err);
      error.value = annotationRequestError(err, "Failed to save knee annotation.");
      return false;
    } finally {
      isSaving.value = false;
    }
  };

  const findPendingIndex = (start: number, end: number) => {
    for (let index = start; index < end; index += 1) {
      const sample = samples.value[index];
      if (sample && !isManuallyAnnotated(sample)) return index;
    }
    return -1;
  };

  const saveAndNext = async () => {
    if (!(await save())) return false;

    if (isReviewComplete.value) return true;

    let nextIndex = findPendingIndex(
      currentIndex.value + 1,
      samples.value.length,
    );

    if (nextIndex === -1) {
      nextIndex = findPendingIndex(0, currentIndex.value + 1);
    }

    if (nextIndex !== -1) {
      currentIndex.value = nextIndex;
      loadCurrentSample();
    }

    return true;
  };

  const clear = async () => {
    const sample = currentSample.value;
    if (!sample || isSaving.value) return;

    isSaving.value = true;
    error.value = null;

    try {
      const cleared = await datasetAnnotationService.clear(sample.id);

      if (session.value) {
        session.value.samples[currentIndex.value] = mergeSavedSample(sample, {
          ...cleared,
          knee_annotation: null,
          target_label: null,
        });
      }

      loadCurrentSample();
    } catch (err) {
      console.error(err);
      error.value = annotationRequestError(err, "Failed to clear knee annotation.");
    } finally {
      isSaving.value = false;
    }
  };

  const previous = () => {
    if (isSaving.value || currentIndex.value <= 0) return;
    currentIndex.value -= 1;
    loadCurrentSample();
  };

  const next = () => {
    if (isSaving.value || currentIndex.value >= samples.value.length - 1) return;
    currentIndex.value += 1;
    loadCurrentSample();
  };

  return {
    session,
    samples,
    currentSample,
    currentIndex,
    fps,
    annotation,
    targetLabel,
    labelledCount,
    inheritedLabelCount,
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
    save,
    saveAndNext,
    clear,
    previous,
    next,
  };
}
