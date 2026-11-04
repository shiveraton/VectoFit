import { computed, onMounted, ref } from "vue";
import { invalidateModels } from "./useModels";
import {
  type AlgorithmOption,
  type FeatureOption,
  trainingService,
  type TrainingJob,
  type WorkflowStep,
  type PredictionTarget,
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
const workflowSteps = ref<WorkflowStep[]>(trainingService.getWorkflowStep());

const selectedDatasetIds = ref<number[]>([]);
const selectedViewAngle = ref<ViewAngle | null>(null);
const predictionTarget = ref<PredictionTarget>("binary_form");
const selectedAlgorithmId = ref<string>("xgboost");

const hyperparameters = ref<Record<string, unknown>>({});
const testSize = ref<number>(0.3);
const randomSeed = ref<number>(42);

const isLoading = ref(false);
const isTraining = ref(false);
const isInitialized = ref(false);
const error = ref<string | null>(null);

export type ViewAngle = "diagonal" | "frontal" | "sagittal";

const setErrorState = (err: unknown) => {
  const responseData =
    typeof err === "object" && err !== null && "response" in err
      ? (err as { response?: { data?: unknown } }).response?.data
      : undefined;

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
      workflow,
    ] = await Promise.all([
      trainingService.getTrainingJobs(),
      datasetService.getDatasets(),
      Promise.resolve(trainingService.getAvailableFeatures()),
      Promise.resolve(trainingService.getAvailableAlgorithms()),
      Promise.resolve(trainingService.getWorkflowStep()),
    ]);

    trainingJobs.value = trainingJobsResponse;
    selectedJob.value =
      trainingJobs.value.find((job) => job.id === selectedJob.value?.id) ??
      trainingJobs.value[0] ??
      null;
    datasets.value = datasetsResponse;
    features.value = featureOptions;
    algorithms.value = algorithmOptions;
    workflowSteps.value = workflow;

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

    if (predictionTarget.value === "binary_form") {
      return (stats?.labelled_sample_count ?? 0) > 0;
    }

    const errorCount = Object.values(stats?.error_label_counts ?? {}).reduce(
      (sum, count) => sum + count,
      0,
    );
    return (stats?.good_count ?? 0) > 0 && errorCount > 0;
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
    description: "All recorded model experiments",
    icon: "R",
    variant: "samples" as const,
  },
  {
    label: "Completed Runs",
    value: completedJobs.value.length,
    description: "Successfully finished experiments",
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

  const viewPart = selectedViewAngle.value
    ? selectedViewAngle.value
    : "No view";

  const featurePart = `${selectedFeaturesCount.value} feature(s)`;
  const targetPart =
    predictionTarget.value === "binary_form"
      ? "Correct vs incorrect"
      : "Error type";
  const algorithmPart = selectedAlgorithm.value?.name ?? "No algorithm";

  return `${datasetPart} · ${viewPart} · ${targetPart} · ${featurePart} · ${algorithmPart}`;
});

const selectViewAngle = (angle: ViewAngle) => {
  selectedViewAngle.value = angle;

  const allowedIds = new Set(
    filteredDatasets.value.map((dataset) => dataset.id),
  );

  selectedDatasetIds.value = selectedDatasetIds.value.filter((id) =>
    allowedIds.has(id),
  );
};

const toggleDataset = (datasetId: number) => {
  const index = selectedDatasetIds.value.indexOf(datasetId);

  if (index >= 0) {
    selectedDatasetIds.value.splice(index, 1);
    return;
  }

  selectedDatasetIds.value.push(datasetId);
};

const setPredictionTarget = (target: PredictionTarget) => {
  predictionTarget.value = target;
  const allowedIds = new Set(
    filteredDatasets.value.map((dataset) => dataset.id),
  );
  selectedDatasetIds.value = selectedDatasetIds.value.filter((id) =>
    allowedIds.has(id),
  );
};

const selectAlgorithm = (algorithmId: string) => {
  selectedAlgorithmId.value = algorithmId;
};

const toggleFeature = (featureId: string) => {
  const feature = features.value.find((item) => item.id === featureId);

  if (feature) {
    feature.selected = !feature.selected;
  }
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

  isTraining.value = true;
  error.value = null;

  try {
    const job = await trainingService.startTraining({
      dataset_ids: selectedDatasetIds.value,
      algorithm: selectedAlgorithm.value.id,
      view_angle: selectedViewAngle.value!,
      prediction_target: predictionTarget.value,
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

    const responseData =
      typeof err === "object" && err !== null && "response" in err
        ? (err as { response?: { data?: unknown } }).response?.data
        : undefined;
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
    isTraining.value = false;
  }
};

export function useTraining() {
  onMounted(() => {
    fetchTrainingData();
  });

  return {
    trainingJobs,
    datasets,
    features,
    algorithms,
    workflowSteps,
    selectedDatasetIds,
    selectedDatasets,
    selectedViewAngle,
    predictionTarget,
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
    selectViewAngle,
    setPredictionTarget,
    toggleDataset,
    selectAlgorithm,
    toggleFeature,
    setHyperparameter,
    setTestSize,
    setRandomSeed,
    startTraining,
  };
}
