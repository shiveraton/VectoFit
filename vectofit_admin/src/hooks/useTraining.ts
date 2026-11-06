import { computed, onMounted, onUnmounted, ref } from "vue";
import { invalidateModels } from "./useModels";
import {
  type AlgorithmOption,
  type FeatureOption,
  trainingService,
  type TrainingJob,
} from "../services/trainingService";
import { datasetService, type Dataset } from "../services/datasetService";

const trainingJobs = ref<TrainingJob[]>([]);

const selectedJob = ref<TrainingJob | null>(null);

const selectJob = (jobId: number) => {
  const job = trainingJobs.value.find((j) => j.id === jobId);
  if (job) {
    selectedJob.value = job;
  }
};
const datasets = ref<Dataset[]>([]);
const features = ref<FeatureOption[]>([]);
const algorithms = ref<AlgorithmOption[]>([]);

const selectedDatasetIds = ref<number[]>([]);
const selectedViewAngle = ref<ViewAngle | null>("frontal");
const selectedAlgorithmId = ref<string>("xgboost");

const hyperparameters = ref<Record<string, unknown>>({});
const testSize = ref<number>(0.3);
const randomSeed = ref<number>(42);

const isLoading = ref(false);
const isSubmitting = ref(false);
const isInitialized = ref(false);
const error = ref<string | null>(null);

export type ViewAngle = "diagonal" | "frontal" | "sagittal";

const responseDataFor = (err: unknown): unknown =>
  typeof err === "object" && err !== null && "response" in err
    ? (err as { response?: { data?: unknown } }).response?.data
    : undefined;

const setErrorState = (err: unknown) => {
  const responseData = responseDataFor(err);

  if (typeof responseData === "object" && responseData !== null) {
    const data = responseData as Record<string, unknown>;
    for (const key of ["detail", "error_message", "message"]) {
      if (typeof data[key] === "string" && data[key]) {
        error.value = data[key] as string;
        return;
      }
    }

    const messages: string[] = [];
    const collect = (value: unknown, prefix: string) => {
      if (typeof value === "string") {
        messages.push(prefix ? `${prefix}: ${value}` : value);
      } else if (Array.isArray(value)) {
        value.forEach((item) => collect(item, prefix));
      } else if (typeof value === "object" && value !== null) {
        Object.entries(value as Record<string, unknown>).forEach(
          ([key, item]) => collect(item, prefix ? `${prefix}.${key}` : key),
        );
      }
    };
    collect(data, "");
    if (messages.length) {
      error.value = messages.join(" · ");
      return;
    }
  }

  if (err instanceof Error) {
    error.value = err.message;
    return;
  }

  if (typeof err === "string") {
    error.value = err;
    return;
  }

  error.value = "An unexpected error occurred during training.";
};

const updateTrainingJobs = (jobs: TrainingJob[]) => {
  const previous = new Map(trainingJobs.value.map((job) => [job.id, job.status]));
  trainingJobs.value = jobs.filter(
    (job) =>
      job.prediction_target === "knee_alignment" &&
      job.feature_schema_version === "fppa_v2",
  );
  const newlyCompleted = trainingJobs.value.some(
    (job) => job.status === "COMPLETED" && previous.get(job.id) !== "COMPLETED",
  );
  if (newlyCompleted) {
    invalidateModels();
  }
  selectedJob.value =
    trainingJobs.value.find((job) => job.id === selectedJob.value?.id) ??
    trainingJobs.value[0] ??
    null;
};

const refreshTrainingJobs = async () => {
  try {
    updateTrainingJobs(await trainingService.getTrainingJobs());
    error.value = null;
  } catch (err: unknown) {
    setErrorState(err);
  }
};

const fetchTrainingData = async (force = false) => {
  if (isInitialized.value && !force) {
    return;
  }

  isLoading.value = true;
  error.value = null;

  try {
    const [
      trainingJobsResponse,
      datasetsResponse,
      featureOptions,
      algorithmOptions,
    ] = await Promise.all([
      trainingService.getTrainingJobs(),
      datasetService.getDatasets(),
      Promise.resolve(trainingService.getAvailableFeatures()),
      Promise.resolve(trainingService.getAvailableAlgorithms()),
    ]);

    updateTrainingJobs(trainingJobsResponse);
    datasets.value = datasetsResponse;
    features.value = featureOptions;
    algorithms.value = algorithmOptions;

    if (
      !algorithmOptions.some(
        (algorithm) => algorithm.id === selectedAlgorithmId.value,
      )
    ) {
      selectedAlgorithmId.value = algorithmOptions[0]?.id ?? "xgboost";
    }

    isInitialized.value = true;
  } catch (err: unknown) {
    console.error("Training initialization error:", err);
    setErrorState(err);
    isInitialized.value = false;
  } finally {
    isLoading.value = false;
  }
};

const availableDatasets = computed(() =>
  datasets.value.filter(
    (dataset) =>
      dataset.status === "READY" &&
      dataset.purpose === "training" &&
      dataset.is_usable_for_training === true,
  ),
);

const filteredDatasets = computed(() => {
  if (!selectedViewAngle.value) {
    return [];
  }

  return availableDatasets.value.filter((dataset) => {
    const angle = selectedViewAngle.value!;
    const stats = dataset.angle_training_stats?.[angle];
    if (!(dataset.view_angles ?? []).includes(angle)) return false;

    return (stats?.knee_target_sample_count ?? 0) > 0;
  });
});

const selectedDatasets = computed(() =>
  datasets.value.filter((dataset) =>
    selectedDatasetIds.value.includes(dataset.id),
  ),
);

const selectedAlgorithm = computed(
  () =>
    algorithms.value.find(
      (algorithm) => algorithm.id === selectedAlgorithmId.value,
    ) ?? null,
);

const selectedFeatures = computed(() =>
  features.value.filter((feature) => feature.selected),
);

const selectedFeaturesCount = computed(() => selectedFeatures.value.length);

const activeJobs = computed(() =>
  trainingJobs.value.filter(
    (job) => job.status === "PENDING" || job.status === "RUNNING",
  ),
);

const isTraining = computed(() => isSubmitting.value || activeJobs.value.length > 0);

const completedJobs = computed(() =>
  trainingJobs.value.filter((job) => job.status === "COMPLETED"),
);

const bestF1Score = computed(() => {
  const scores = completedJobs.value
    .map((job) => {
      const value = job.metrics?.f1;
      return typeof value === "number" ? value : null;
    })
    .filter((value): value is number => value !== null);

  if (!scores.length) {
    return "--";
  }

  return `${(Math.max(...scores) * 100).toFixed(1)}%`;
});

const canStartTraining = computed(
  () =>
    selectedDatasetIds.value.length > 0 &&
    selectedViewAngle.value !== null &&
    selectedFeaturesCount.value > 0 &&
    selectedAlgorithm.value !== null &&
    !isTraining.value,
);

const summaryCards = computed(() => [
  {
    label: "Total Runs",
    value: trainingJobs.value.length,
    description: "FPPA v2 knee-alignment experiments",
    icon: "R",
    variant: "samples" as const,
  },
  {
    label: "Completed Runs",
    value: completedJobs.value.length,
    description: "Completed FPPA M1 runs",
    icon: "C",
    variant: "correct" as const,
  },
  {
    label: "Active Jobs",
    value: activeJobs.value.length,
    description: "Pending or running jobs",
    icon: "T",
    variant: "samples" as const,
  },
  {
    label: "Failed Runs",
    value: trainingJobs.value.filter((j) => j.status === "FAILED").length,
    description: "Experiments that ended with errors",
    icon: "F",
    variant: "incorrect" as const,
  },
]);

const configSummaryText = computed(() => {
  const datasetPart = selectedDatasetIds.value.length
    ? `${selectedDatasetIds.value.length} dataset(s)`
    : "No datasets";

  return `${datasetPart} · frontal view · FPPA knee alignment · six fixed FPPA features · XGBoost M1`;
});

const toggleDataset = (datasetId: number) => {
  const index = selectedDatasetIds.value.indexOf(datasetId);

  if (index >= 0) {
    selectedDatasetIds.value.splice(index, 1);
    return;
  }

  selectedDatasetIds.value.push(datasetId);
};

const setHyperparameter = (name: string, value: unknown) => {
  hyperparameters.value[name] = value;
};

const setTestSize = (value: number) => {
  testSize.value = value;
};

const setRandomSeed = (value: number) => {
  randomSeed.value = value;
};

const startTraining = async () => {
  if (!canStartTraining.value || !selectedAlgorithm.value) {
    return null;
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    const job = await trainingService.startTraining({
      dataset_ids: selectedDatasetIds.value,
      algorithm: selectedAlgorithm.value.id,
      view_angle: selectedViewAngle.value!,
      prediction_target: "knee_alignment",
      feature_selection: selectedFeatures.value.map((feature) => feature.id),
      hyperparameters: hyperparameters.value,
      test_size: testSize.value,
      random_seed: randomSeed.value,
    });

    trainingJobs.value.unshift(job);
    selectedJob.value = job;

    if (job.status === "COMPLETED") {
      invalidateModels();
    }

    return job;
  } catch (err: unknown) {
    console.error("Training start error:", err);

    const responseData = responseDataFor(err);
    if (
      typeof responseData === "object" &&
      responseData !== null &&
      "id" in responseData &&
      typeof (responseData as { id?: unknown }).id === "number" &&
      "status" in responseData &&
      typeof (responseData as { status?: unknown }).status === "string"
    ) {
      const failedJob = responseData as TrainingJob;
      trainingJobs.value = [
        failedJob,
        ...trainingJobs.value.filter((job) => job.id !== failedJob.id),
      ];
    }

    setErrorState(err);
    return null;
  } finally {
    isSubmitting.value = false;
  }
};

export function useTraining() {
  let pollTimer: ReturnType<typeof setTimeout> | undefined;
  let mounted = false;
  const poll = async () => {
    if (!mounted) return;
    if (activeJobs.value.length) await refreshTrainingJobs();
    if (mounted) pollTimer = setTimeout(poll, 3000);
  };
  onMounted(async () => {
    mounted = true;
    await fetchTrainingData(true);
    if (mounted) pollTimer = setTimeout(poll, 3000);
  });
  onUnmounted(() => {
    mounted = false;
    clearTimeout(pollTimer);
  });

  return {
    trainingJobs,
    datasets,
    features,
    algorithms,
    selectedDatasetIds,
    selectedDatasets,
    selectedViewAngle,
    selectedAlgorithm,
    selectedAlgorithmId,
    selectedFeatures,
    selectedFeaturesCount,
    hyperparameters,
    testSize,
    randomSeed,
    availableDatasets,
    filteredDatasets,
    activeJobs,
    completedJobs,
    summaryCards,
    configSummaryText,
    bestF1Score,
    isLoading,
    isTraining,
    isInitialized,
    error,
    selectedJob,
    selectJob,
    canStartTraining,
    fetchTrainingData,
    refreshTrainingJobs,
    toggleDataset,
    setHyperparameter,
    setTestSize,
    setRandomSeed,
    startTraining,
  };
}
