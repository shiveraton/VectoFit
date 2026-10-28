import { ref, computed, onMounted } from "vue";
import {
  modelService,
  type ModelState,
  type ModelRegistryRecord,
} from "../services/modelService";

const models = ref<ModelRegistryRecord[]>([]);
const modelState = ref<ModelState | null>(null);
const selectedModelId = ref<number | null>(null);

const isLoading = ref<boolean>(false);
const isStateLoading = ref(false);
const isInitialized = ref(false);
const error = ref<string | null>(null);

const fetchModelState = async (id: number) => {
  isStateLoading.value = true;
  error.value = null;

  try {
    modelState.value = await modelService.getModelState(id);
  } catch (err: unknown) {
    error.value =
      err instanceof Error ? err.message : "Failed to load model state.";

    modelState.value = null;
  } finally {
    isStateLoading.value = false;
  }
};

export function useModels() {
  const fetchModels = async (force = false) => {
    if (isInitialized.value && !force) return;

    isLoading.value = true;
    error.value = null;

    try {
      models.value = await modelService.getModels();

      const active = models.value.find((model) => model.is_active);
      const nextId = active?.id ?? models.value[0]?.id ?? null;

      selectedModelId.value = nextId;

      if (nextId != null) {
        await fetchModelState(nextId);
      } else {
        modelState.value = null;
      }

      isInitialized.value = true;
    } catch (err: unknown) {
      error.value =
        err instanceof Error ? err.message : "Failed to load model registry.";

      isInitialized.value = true;
    } finally {
      isLoading.value = false;
    }
  };

  const selectModel = async (id: number) => {
    if (selectedModelId.value === id && modelState.value?.id === id) {
      return;
    }

    selectedModelId.value = id;
    await fetchModelState(id);
  };

  const selectedModel = computed(
    () =>
      models.value.find((model) => model.id === selectedModelId.value) ?? null,
  );

  const latestModel = computed(() => models.value[0] ?? null);

  /*
  const activeDeploymentsCount = computed(() => {
    return models.value.reduce((acc, m) => {
      return acc + m.versions.filter((v) => v.status === "active").length;
    }, 0);
  }); */

  const summaryCards = computed(() => {
    const state = modelState.value;
    const metrics = state?.evaluation;

    return [
      {
        label: "CURRENT VERSION",
        value: state ? `v${state.version}` : "—",
        description: state?.name ?? "No model registered",
      },
      {
        label: "ACCURACY",
        value:
          metrics?.accuracy != null
            ? `${(metrics.accuracy * 100).toFixed(1)}%`
            : "—",
        description: metrics ? "Held out test set" : "No evaluation available",
      },
      {
        label: "F1 SCORE",
        value: metrics?.f1 != null ? `${(metrics.f1 * 100).toFixed(1)}%` : "—",
        description: metrics
          ? "Binary classification F1"
          : "No evaluation available",
      },
      {
        label: "FEATURES",
        value: state?.features.selected.length ?? "—",
        description: "Model input features",
      },
    ];
  });

  onMounted(fetchModels);

  const workflowSteps = computed(() => [
    {
      step: "01",
      title: "Model Registration",
      description:
        "Upload weight artifacts, define input schemas, and register metadata tags.",
    },
    {
      step: "02",
      title: "Biomechanical Benchmark",
      description:
        "Run accuracy and posture movement validation against reference datasets.",
    },
    {
      step: "03",
      title: "Endpoint Provisioning",
      description:
        "Configure environment, memory allocation, and auto-scaling constraints.",
    },
    {
      step: "04",
      title: "Active Inference Monitoring",
      description:
        "Serve real-time API requests and monitor latency, throughput, and memory metrics.",
    },
  ]);

  /*
  const openDeployModal = (modelId: string, version: ModelVersion) => {
    selectedTarget.value = { modelId, version };
    isDeployModalOpen.value = true;
  };

  const closeDeployModal = () => {
    selectedTarget.value = null;
    isDeployModalOpen.value = false;
  };

  const handleDeploy = async (config: {
    environment: "staging" | "production";
    minReplicas: number;
    maxReplicas: number;
  }) => {
    if (!selectedTarget.value) return;
    const { modelId, version } = selectedTarget.value;

    version.status = "building";

    try {
      const payload: DeployPayload = {
        modelId,
        versionId: version.id,
        ...config,
      };
      await modelService.deployVersion(payload);
      version.status = "active";
      version.environment = config.environment;
      closeDeployModal();
    } catch (err) {
      version.status = "failed";
    }
  };

  const handleUndeploy = async (modelId: string, version: ModelVersion) => {
    const previousStatus = version.status;
    version.status = "building";

    try {
      await modelService.undeployVersion(modelId, version.id);
      version.status = "inactive";
      version.environment = undefined;
      version.endpointUrl = undefined;
    } catch (err) {
      version.status = previousStatus;
    }
  }; */

  return {
    models,
    modelState,
    selectedModel,
    latestModel,
    selectedModelId,
    isLoading,
    isStateLoading,
    isInitialized,
    error,
    summaryCards,
    workflowSteps,
    fetchModels,
    fetchModelState,
    selectModel,
  };
}
