import { computed, onMounted, ref } from "vue";
import {
  type AlgorithmOption,
  type FeatureOption,
  trainingService,
  type TrainingJob,
  type WorkflowStep,
} from "../services/trainingService";
import { datasetService, type Dataset } from "../services/datasetService";

const trainingJobs = ref<TrainingJob[]>([]);
const datasets = ref<Dataset[]>([]);
const features = ref<FeatureOption[]>([]);
const algorithms = ref<AlgorithmOption[]>([]);
const workflowSteps = ref<WorkflowStep[]>(trainingService.getWorkflowStep());

const selectedDatasetIds = ref<number[]>([]);
const selectedViewAngle = ref<ViewAngle | null>(null);
const selectedAlgorithmId = ref<string>("xgboost");

const hyperparameters = ref<Record<string, unknown>>({});
const testSize = ref<number>(0.3);
const randomSeed = ref<number>(42);

const isLoading = ref(false);
const isTraining = ref(false);
const isInitialized = ref(false);
const error = ref<string | null>(null);

export type ViewAngle = "diagonal" | "frontal" | "sagittal";

const VIEW_ANGLE_BY_ID: Record<number, ViewAngle> = {
  1: "diagonal",
  2: "frontal",
  3: "sagittal",
};

const setErrorState = (err: unknown) => {
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
  console.log("fetchTrainingData() called");

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
    datasets.value = datasetsResponse;
    console.log("Training datasets response:", datasetsResponse);
    console.log("First dataset view_angle:", datasetsResponse[0]?.view_angle);
    console.log(
      "ALL DATASETS:",
      datasets.value.map((dataset) => ({
        id: dataset.id,
        name: dataset.name,
        view_angle: dataset.view_angle,
        status: dataset.status,
        usable: dataset.is_usable_for_training,
        samples: dataset.sample_count,
        labelled: dataset.labelled_sample_count,
      })),
    );

    console.log(
      "AVAILABLE DATASETS:",
      availableDatasets.value.map((dataset) => ({
        id: dataset.id,
        name: dataset.name,
        view_angle: dataset.view_angle,
        status: dataset.status,
        usable: dataset.is_usable_for_training,
      })),
    );

    console.log(
      "FILTERED DATASETS:",
      filteredDatasets.value.map((dataset) => ({
        id: dataset.id,
        name: dataset.name,
        view_angle: dataset.view_angle,
      })),
    );
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
      dataset.status === "READY" && dataset.is_usable_for_training === true,
  ),
);

const filteredDatasets = computed(() => {
  if (!selectedViewAngle.value) {
    return [];
  }

  return availableDatasets.value.filter(
    (dataset) =>
      VIEW_ANGLE_BY_ID[dataset.view_angle ?? -1] === selectedViewAngle.value,
  );
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
    label: "Training Runs",
    value: trainingJobs.value.length,
    description: "Recorded model experiments",
    icon: "R",
    variant: "samples" as const,
  },
  {
    label: "Selected Datasets",
    value: selectedDatasetIds.value.length,
    description: "Datasets included in this run",
    icon: "D",
    variant: "samples" as const,
  },
  {
    label: "Active Jobs",
    value: activeJobs.value.length,
    description: "Pending or running jobs",
    icon: "T",
    variant: "samples" as const,
  },
  {
    label: "Best F1 Score",
    value: bestF1Score.value,
    description: "Best completed experiment",
    icon: "F1",
    variant: "correct" as const,
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

  const algorithmPart = selectedAlgorithm.value?.name ?? "No algorithm";

  return `${datasetPart} · ${viewPart} · ${featurePart} · ${algorithmPart}`;
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
      feature_selection: selectedFeatures.value.map((feature) => feature.id),
      hyperparameters: hyperparameters.value,
      test_size: testSize.value,
      random_seed: randomSeed.value,
    });

    trainingJobs.value.unshift(job);

    return job;
  } catch (err: unknown) {
    console.error("Training start error:", err);
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
    canStartTraining,
    fetchTrainingData,
    selectViewAngle,
    toggleDataset,
    selectAlgorithm,
    toggleFeature,
    setHyperparameter,
    setTestSize,
    setRandomSeed,
    startTraining,
  };
}
