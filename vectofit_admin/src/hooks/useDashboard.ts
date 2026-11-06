import { computed } from "vue";

import { useModels } from "./useModels";
import { useDatasets } from "./useDatasets";
import { useTraining } from "./useTraining";

export function useDashboard() {
  const { models, fetchModels, error: modelError } = useModels();

  const { datasets, fetchDatasets, errorMessage: datasetError } = useDatasets();

  const { trainingJobs, fetchTrainingData, error: trainingError } = useTraining();

  const currentModel = computed(
    () =>
      models.value.find((model) => model.is_active) ?? models.value[0] ?? null,
  );

  const activeJobsCount = computed(
    () =>
      trainingJobs.value.filter(
        (job) => job.status === "RUNNING" || job.status === "PENDING",
      ).length,
  );

  const dashboardCards = computed(() => [
    {
      label: "Registered Datasets",
      value: datasets.value.length,
      description: "Available benchmark datasets",
      icon: "D",
      variant: "samples" as const,
    },

    {
      label: "Registered Models",
      value: models.value.length,
      description: "Total trained model versions",
      icon: "M",
      variant: "version" as const,
    },

    {
      label: "Current Model",
      value: currentModel.value ? `v${currentModel.value.version}` : "None",
      description: currentModel.value?.name ?? "No registered model",
      icon: "M",
      variant: "correct" as const,
    },

    {
      label: "Active Training Runs",
      value: activeJobsCount.value,
      description: "Currently executing pipeline jobs",
      icon: "T",
      variant: "samples" as const,
    },
  ]);

  const error = computed(() => [modelError.value, datasetError.value, trainingError.value].filter(Boolean).join(" "));

  const fetchAllDashboardData = async (force = false) => {
    datasetError.value = "";
    await Promise.all([fetchModels(force), fetchDatasets(force), fetchTrainingData(force)]);
  };

  return {
    error,
    dashboardCards,
    currentModel,
    fetchAllDashboardData,
  };
}
