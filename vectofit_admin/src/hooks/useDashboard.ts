import { computed } from "vue";
import { useModels } from "./useModels";
import { useDatasets } from "./useDatasets";
import { useTraining } from "./useTraining";

export function useDashboard() {
  const { models, fetchModels } = useModels();
  const { datasets, fetchDatasets } = useDatasets();
  const { trainingJobs, fetchTrainingJobs } = useTraining();

  const activeModel = computed(() => {
    for (const model of models.value) {
      const activeVersion = model.versions.find((v) => v.status === "active");
      if (activeVersion) {
        return {
          modelName: model.name,
          framework: model.framework,
          ...activeVersion,
        };
      }
    }
    return null;
  });

  const activeJobsCount = computed(
    () =>
      trainingJobs.value.filter(
        (j) => j.status === "running" || j.status === "queued",
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
      description: "Total model architectures",
      icon: "M",
      variant: "version" as const,
    },
    {
      label: "Active Production Endpoint",
      value: activeModel.value ? activeModel.value.version : "None",
      description: activeModel.value
        ? activeModel.value.modelName
        : "No model deployed",
      icon: "E",
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
    await Promise.all([fetchModels(), fetchDatasets(), fetchTrainingJobs()]);
  };

  return {
    dashboardCards,
    activeModel,
    fetchAllDashboardData,
  };
}
