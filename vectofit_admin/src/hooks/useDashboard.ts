import { computed } from "vue";

import { useModels } from "./useModels";
import { useDatasets } from "./useDatasets";
import { useTraining } from "./useTraining";

export function useDashboard() {
  const { models, fetchModels } = useModels();

  const { datasets, fetchDatasets } = useDatasets();

  const { trainingJobs, fetchTrainingData } = useTraining();

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

  const fetchAllDashboardData = async () => {
    await Promise.all([fetchModels(), fetchDatasets(), fetchTrainingData()]);
  };

  return {
    dashboardCards,
    currentModel,
    fetchAllDashboardData,
  };
}
