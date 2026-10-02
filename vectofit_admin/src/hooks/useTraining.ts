import { ref, computed } from "vue";
import {
  type AlgorithmOption,
  type FeatureOption,
  trainingService,
  type TrainingJob,
  type TrainingTask,
  type WorkflowStep,
} from "../services/trainingService";

const trainingTasks = ref<TrainingTask[]>([]);
const trainingJobs = ref<TrainingJob[]>([]);
const features = ref<FeatureOption[]>([]);
const algorithm = ref<AlgorithmOption | null>(null);
const workflowSteps = ref<WorkflowStep[]>([]);

const isLoading = ref(false);
const isInitialized = ref<boolean>(false);
const error = ref<string | null>(null);
const selectedDataset = ref<string | null>(null);
const selectedTaskId = ref<string>("task-quality");

const setTasks = (tasks: TrainingTask[]) => {
  trainingTasks.value = tasks;
};

const setErrorState = (err: unknown) => {
  if (err instanceof Error) {
    error.value = err.message;
  } else if (typeof err === "string") {
    error.value = err;
  } else {
    error.value =
      "An unexpected error occurred during training initialization.";
  }
};

const fetchTrainingConfig = async (force = false) => {
  if (isInitialized.value && !force) return;

  isLoading.value = true;
  error.value = null;

  try {
    const [tasks, jobs, featureList, selectedAlgo, steps] = await Promise.all([
      trainingService.getTrainingTasks(),
      trainingService.getTrainingJobs(),
      trainingService.getAvailableFeatures(),
      trainingService.getAlgorithm(),
      trainingService.getWorkflowStep(),
    ]);

    setTasks(tasks);
    trainingJobs.value = jobs;
    features.value = featureList;
    algorithm.value = selectedAlgo;
    workflowSteps.value = steps;

    isInitialized.value = true;
  } catch (err: unknown) {
    console.error("Training initialization error:", err);
    setErrorState(err);
    isInitialized.value = false;
  } finally {
    isLoading.value = false;
  }
};

export function useTraining() {
  const fetchTrainingJobs = async (force = false) => {
    if (isInitialized.value && !force) return;

    isLoading.value = true;
    error.value = null;

    try {
      const [tasksRes, jobsRes, featuresRes, algoRes] = await Promise.all([
        trainingService.getTrainingTasks(),
        trainingService.getTrainingJobs(),
        trainingService.getAvailableFeatures(),
        trainingService.getAlgorithm(),
      ]);

      trainingTasks.value = tasksRes;
      trainingJobs.value = jobsRes;
      features.value = featuresRes;
      algorithm.value = algoRes;
      workflowSteps.value = trainingService.getWorkflowStep();

      isInitialized.value = true;
    } catch (err: any) {
      error.value = err.message || "Failed to load training data";
    } finally {
      isLoading.value = false;
    }
  };

  const activeJobs = computed(() =>
    trainingJobs.value.filter(
      (j) => j.status === "running" || j.status === "queued",
    ),
  );

  const completedJobs = computed(() =>
    trainingJobs.value.filter((j) => j.status === "completed"),
  );

  const selectedFeaturesCount = computed(
    () => features.value.filter((f) => f.selected).length,
  );

  const summaryCards = computed(() => [
    {
      label: "Training Runs",
      value: trainingTasks.value.length,
      description: "Recorded experiments",
      icon: "R",
      variant: "samples" as const,
    },
    {
      label: "Active Dataset",
      value: selectedDataset.value || "None",
      description: "Dataset selected for training",
      icon: "D",
      variant: "samples" as const,
    },
    {
      label: "Model Tasks",
      value: trainingTasks.value.length,
      description: "Classification objectives",
      icon: "T",
      variant: "samples" as const,
    },
    {
      label: "Best F1 Score",
      value: "--",
      description: "No evaluated models yet",
      icon: "F1",
      variant: "incorrect" as const,
    },
  ]);

  const configSummaryText = computed(() => {
    const selectedTaskName =
      trainingTasks.value.find((t) => t.id === selectedTaskId.value)?.title ||
      "No Task";
    return `${algorithm.value?.name} · ${selectedFeaturesCount.value} features · ${selectedTaskName}`;
  });

  const toggleFeature = (id: string) => {
    const item = features.value.find((f) => f.id === id);
    if (item) {
      item.selected = !item.selected;
    }
  };

  const selectTask = (id: string) => {
    selectedTaskId.value = id;
  };

  return {
    trainingTasks,
    trainingJobs,
    isLoading,
    activeJobs,
    completedJobs,
    selectedDataset,
    selectedTaskId,
    features,
    algorithm,
    workflowSteps,
    selectedFeaturesCount,
    summaryCards,
    configSummaryText,
    toggleFeature,
    selectTask,
    fetchTrainingJobs,
    fetchTrainingConfig,
  };
}
