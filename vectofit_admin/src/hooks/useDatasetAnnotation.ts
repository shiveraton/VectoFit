import { computed, ref } from "vue";
import {
  datasetAnnotationService,
  type AnnotationCriteria,
  type CriterionKey,
  type DatasetSample,
  type AnnotationSession,
} from "../services/datasetAnnotationService";

const ERROR_LABELS: Record<CriterionKey, string> = {
  depth: "insufficient_depth",
  knee: "knee_valgus",
  trunk: "excessive_trunk_lean",
  symmetry: "asymmetry",
  foot: "foot_instability",
  completion: "incomplete_rep",
};

const emptyCriteria = (): AnnotationCriteria => ({
  depth: null,
  knee: null,
  trunk: null,
  symmetry: null,
  foot: null,
  completion: null,
});

export function useDatasetAnnotation() {
  const session = ref<AnnotationSession | null>(null);
  const currentIndex = ref(0);
  const criteria = ref<AnnotationCriteria>(emptyCriteria());
  const errorLabel = ref("");
  const errorLabelEdited = ref(false);

  const isLoading = ref(false);
  const isSaving = ref(false);
  const error = ref<string | null>(null);

  const currentSample = computed<DatasetSample | null>(
    () => session.value?.samples[currentIndex.value] ?? null,
  );

  const samples = computed(() => session.value?.samples ?? []);

  const fps = computed(() => session.value?.fps ?? 0);

  const verdict = computed<"CORRECT" | "INCORRECT" | "PENDING">(() => {
    const values = Object.values(criteria.value);

    if (values.some((value) => value === false)) {
      return "INCORRECT";
    }

    if (values.every((value) => value === true)) {
      return "CORRECT";
    }

    return "PENDING";
  });

  const suggestedLabels = computed(() =>
    (Object.entries(criteria.value) as [CriterionKey, boolean | null][])
      .filter(([, value]) => value === false)
      .map(([key]) => ERROR_LABELS[key])
      .join(","),
  );

  const labelledCount = computed(
    () => samples.value.filter((sample) => sample.is_correct !== null).length,
  );

  const load = async (datasetId: number) => {
    isLoading.value = true;
    error.value = null;

    try {
      session.value = await datasetAnnotationService.getSession(datasetId);

      currentIndex.value = 0;
      loadCurrentSample();
    } catch (err) {
      console.error(err);
      error.value = "Unable to load annotation data.";
    } finally {
      isLoading.value = false;
    }
  };

  const loadCurrentSample = () => {
    const sample = currentSample.value;

    if (!sample) {
      criteria.value = emptyCriteria();
      errorLabel.value = "";
      return;
    }

    /*
     * We do not yet persist the six criteria individually.
     * Reconstruct the visible state from the saved final annotation.
     */
    if (sample.is_correct === true) {
      criteria.value = {
        depth: true,
        knee: true,
        trunk: true,
        symmetry: true,
        foot: true,
        completion: true,
      };
    } else if (sample.is_correct === false) {
      criteria.value = emptyCriteria();

      const labels = sample.error_label.split(",").map((label) => label.trim());

      (Object.entries(ERROR_LABELS) as [CriterionKey, string][]).forEach(
        ([key, label]) => {
          criteria.value[key] = labels.includes(label) ? false : true;
        },
      );
    } else {
      criteria.value = emptyCriteria();
    }

    errorLabel.value = sample.error_label;
    errorLabelEdited.value = false;
  };

  const setCriterion = (key: CriterionKey, value: boolean) => {
    criteria.value[key] = criteria.value[key] === value ? null : value;

    if (!errorLabelEdited.value) {
      errorLabel.value = suggestedLabels.value;
    }
  };

  const save = async () => {
    if (!currentSample.value || verdict.value === "PENDING") {
      return false;
    }

    isSaving.value = true;
    error.value = null;

    try {
      const saved = await datasetAnnotationService.save(
        currentSample.value.id,
        {
          is_correct: verdict.value === "CORRECT",
          error_label: verdict.value === "INCORRECT" ? errorLabel.value : "",
        },
      );

      session.value!.samples[currentIndex.value] = saved;

      return true;
    } catch (err) {
      console.error(err);
      error.value = "Failed to save annotation.";
      return false;
    } finally {
      isSaving.value = false;
    }
  };

  const saveAndNext = async () => {
    const saved = await save();

    if (!saved) {
      return false;
    }

    if (currentIndex.value < samples.value.length - 1) {
      currentIndex.value += 1;
      loadCurrentSample();
    }

    return true;
  };

  const clear = async () => {
    if (!currentSample.value) {
      return;
    }

    isSaving.value = true;

    try {
      const cleared = await datasetAnnotationService.clear(
        currentSample.value.id,
      );

      session.value!.samples[currentIndex.value] = cleared;
      loadCurrentSample();
    } finally {
      isSaving.value = false;
    }
  };

  const previous = () => {
    if (currentIndex.value === 0) return;

    currentIndex.value -= 1;
    loadCurrentSample();
  };

  const next = () => {
    if (currentIndex.value >= samples.value.length - 1) {
      return;
    }

    currentIndex.value += 1;
    loadCurrentSample();
  };

  return {
    session,
    samples,
    currentSample,
    currentIndex,
    fps,
    criteria,
    errorLabel,
    errorLabelEdited,
    verdict,
    labelledCount,
    suggestedLabels,
    isLoading,
    isSaving,
    error,
    load,
    setCriterion,
    save,
    saveAndNext,
    clear,
    previous,
    next,
  };
}
