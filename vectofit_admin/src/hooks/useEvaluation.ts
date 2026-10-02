import { ref, computed } from "vue";

export interface EvaluationModel {
  id: string;
  name: string;
  version: string;
  type: string;
  accuracy?: number;
}

export interface EvaluationMetric {
  id: string;
  name: string;
  description: string;
  selected: boolean;
  category: "form" | "kinematics" | "accuracy" | "performance";
}

export interface EvaluationRecord {
  id: string;
  modelId: string;
  modelName: string;
  datasetName: string;
  score: number;
  status: "COMPLETED" | "RUNNING" | "FAILED" | "PENDING";
  createdAt: string;
  duration: string;
}

export interface WorkflowStep {
  stepNumber: number;
  title: string;
  description: string;
  status: "completed" | "active" | "pending";
}

export interface SummaryCardData {
  label: string;
  value: string | number;
  description: string;
  icon: string;
  variant?: "version" | "samples" | "incorrect" | "correct";
  statusIcon?: boolean;
}

export function useEvaluation() {
  const selectedDataset = ref<Record<string, any> | null>(null);
  const selectedModelId = ref<string | null>(null);
  const evaluations = ref<EvaluationRecord[]>([]);

  const models = ref<EvaluationModel[]>([
    {
      id: "model-v2-4",
      name: "SquatVectorNet-v2.4",
      version: "2.4.0",
      type: "ResNet3D Pose",
      accuracy: 94.2,
    },
    {
      id: "model-v2-3",
      name: "SquatVectorNet-v2.3",
      version: "2.3.1",
      type: "MediaPipe Custom",
      accuracy: 91.8,
    },
    {
      id: "model-v1-0",
      name: "BaselineKinematics-v1",
      version: "1.0.0",
      type: "Linear Biomechanics",
      accuracy: 85.5,
    },
  ]);

  const metrics = ref<EvaluationMetric[]>([
    {
      id: "hip_knee_angle",
      name: "Hip & Knee Flexion Angle",
      description: "Measures joint angle compliance during lowest squat depth.",
      selected: true,
      category: "kinematics",
    },
    {
      id: "barbell_path_dev",
      name: "Barbell Path Deviation",
      description:
        "Tracks horizontal displacement relative to mid-foot baseline.",
      selected: true,
      category: "form",
    },
    {
      id: "valgus_collapse",
      name: "Knee Valgus Detection",
      description:
        "Flags inward knee collapse during concentric movement phase.",
      selected: true,
      category: "form",
    },
    {
      id: "pose_confidence",
      name: "3D Keypoint Confidence",
      description: "Evaluates keypoint tracking reliability under occlusion.",
      selected: false,
      category: "accuracy",
    },
  ]);

  const workflowSteps = ref<WorkflowStep[]>([
    {
      stepNumber: 1,
      title: "Select Model & Reference Set",
      description:
        "Choose an active model checkpoint and baseline evaluation dataset.",
      status: "completed",
    },
    {
      stepNumber: 2,
      title: "Configure Metrics",
      description: "Toggle spatial, temporal, and classification benchmarks.",
      status: "active",
    },
    {
      stepNumber: 3,
      title: "Run Inference & Vector Analysis",
      description: "Compute joint angle vectors against reference kinematics.",
      status: "pending",
    },
    {
      stepNumber: 4,
      title: "Review Score & Biomechanical Breakdown",
      description:
        "Analyze accuracy ratings, flag form deviations, and export report.",
      status: "pending",
    },
  ]);

  const selectTask = (modelId: string) => {
    selectModel(modelId);
  };

  const selectModel = (modelId: string) => {
    selectedModelId.value = selectedModelId.value === modelId ? null : modelId;
  };

  const toggleMetric = (metricId: string) => {
    const metric = metrics.value.find((m) => m.id === metricId);
    if (metric) {
      metric.selected = !metric.selected;
    }
  };

  const setDataset = (dataset: Record<string, any> | null) => {
    selectedDataset.value = dataset;
  };

  const selectedModel = computed(
    () => models.value.find((m) => m.id === selectedModelId.value) ?? null,
  );

  const selectedMetrics = computed(() =>
    metrics.value.filter((m) => m.selected),
  );

  const configSummaryText = computed(() => {
    if (!selectedModel.value && !selectedDataset.value) {
      return "Select a model and dataset to begin evaluation configuration.";
    }

    const modelPart = selectedModel.value
      ? `Model: ${selectedModel.value.name}`
      : "No model selected";
    const datasetPart = selectedDataset.value
      ? `Dataset: ${selectedDataset.value.name || selectedDataset.value.id}`
      : "No dataset selected";
    const metricPart = `${selectedMetrics.value.length} metric(s) enabled`;

    return `${modelPart} | ${datasetPart} | ${metricPart}`;
  });

  const summaryCards = computed<SummaryCardData[]>(() => {
    const totalEvals = evaluations.value.length;
    const completedEvals = evaluations.value.filter(
      (e) => e.status === "COMPLETED",
    );

    const avgScore = completedEvals.length
      ? (
          completedEvals.reduce((acc, curr) => acc + curr.score, 0) /
          completedEvals.length
        ).toFixed(1) + "%"
      : "--";

    const activeMetricsCount = selectedMetrics.value.length;

    return [
      {
        label: "TOTAL EVALUATIONS",
        value: totalEvals,
        description:
          totalEvals > 0
            ? `${totalEvals} evaluation runs executed`
            : "No evaluation runs recorded",
        icon: "bar-chart",
        variant: "samples",
      },
      {
        label: "AVG VECTOR SCORE",
        value: avgScore,
        description: completedEvals.length
          ? "Based on completed runs"
          : "Pending evaluation runs",
        icon: "check-circle",
        variant: "correct",
      },
      {
        label: "SELECTED MODEL",
        value: selectedModel.value ? selectedModel.value.name : "None",
        description: selectedModel.value
          ? `Active version v${selectedModel.value.version}`
          : "No model selected",
        icon: "cpu",
        variant: "version",
      },
      {
        label: "ACTIVE METRICS",
        value: `${activeMetricsCount}/${metrics.value.length}`,
        description: `${activeMetricsCount} benchmark metrics configured`,
        icon: "layers",
        variant: "samples",
      },
    ];
  });

  return {
    selectedDataset,
    selectedModelId,
    selectedModel,
    models,
    metrics,
    evaluations,
    workflowSteps,

    selectedMetrics,
    configSummaryText,
    summaryCards,

    selectTask,
    selectModel,
    toggleMetric,
    setDataset,
  };
}
