import { ref, computed, onMounted } from "vue";
import {
  modelService,
  type Model,
  type ModelVersion,
  type DeployPayload,
  type SummaryCardData,
} from "../services/modelService";

const models = ref<Model[]>([]);
const isLoading = ref<boolean>(false);
const isInitialized = ref<boolean>(false);
const error = ref<string | null>(null);

export function useModels() {
  const selectedTarget = ref<{ modelId: string; version: ModelVersion } | null>(
    null,
  );
  const isDeployModalOpen = ref<boolean>(false);

  const fetchModels = async (force = false) => {
    if (isInitialized.value && !force) return;

    isLoading.value = true;
    error.value = null;

    try {
      models.value = await modelService.getModels();
    } catch (err: any) {
      error.value = err.message || "Failed to load model registry.";
      isInitialized.value = true;
    } finally {
      isLoading.value = false;
    }
  };

  const activeDeploymentsCount = computed(() => {
    return models.value.reduce((acc, m) => {
      return acc + m.versions.filter((v) => v.status === "active").length;
    }, 0);
  });

  const summaryCards = computed<SummaryCardData[]>(() => {
    const totalModels = models.value.length;
    const activeDeploys = activeDeploymentsCount.value;

    let avgLatency = 0;
    let avgAccuracy = 0;
    let activeVersionCount = 0;

    models.value.forEach((m) => {
      m.versions.forEach((v) => {
        if (v.status === "active") {
          avgLatency += v.latencyMs;
          avgAccuracy += v.accuracy;
          activeVersionCount++;
        }
      });
    });

    const displayLatency = activeVersionCount
      ? `${Math.round(avgLatency / activeVersionCount)} ms`
      : "--";
    const displayAccuracy = activeVersionCount
      ? `${((avgAccuracy / activeVersionCount) * 100).toFixed(1)}%`
      : "--";

    return [
      {
        label: "Registered Models",
        value: totalModels,
        description: "Total model architectures registered in Vectofit",
        icon: "version",
        variant: "version",
      },
      {
        label: "Active Deployments",
        value: activeDeploys,
        description: "Endpoints currently serving live inference traffic",
        icon: "correct",
        variant: "correct",
      },
      {
        label: "Avg Inference Latency",
        value: displayLatency,
        description: "Mean response time across active endpoints",
        icon: "samples",
        variant: "samples",
      },
      {
        label: "Mean Posture Accuracy",
        value: displayAccuracy,
        description: "Average movement vector precision score",
        icon: "correct",
        variant: "correct",
      },
    ];
  });

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
  };

  onMounted(fetchModels);

  return {
    models,
    isLoading,
    isInitialized,
    error,
    summaryCards,
    workflowSteps,
    selectedTarget,
    isDeployModalOpen,
    fetchModels,
    openDeployModal,
    closeDeployModal,
    handleDeploy,
    handleUndeploy,
  };
}
