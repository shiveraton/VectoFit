import { computed, onMounted, ref } from "vue";
import {
  modelService,
  type ModelRegistryRecord,
  type ModelState,
} from "../services/modelService";

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
  category: string;
  description: string;
  selected: boolean;
}

export interface EvaluationRecord {
  id: string;
  modelName: string;
  datasetName: string;
  score: number;
  status: "COMPLETED" | "RUNNING" | "FAILED" | "PENDING";
  createdAt: string;
  duration: string;
}

export function useEvaluation() {
  const models = ref<ModelRegistryRecord[]>([]);
  const modelState = ref<ModelState | null>(null);
  const selectedModelId = ref<number | null>(null);

  const isLoading = ref(false);
  const isStateLoading = ref(false);
  const error = ref<string | null>(null);

  const messageFromError = (err: unknown, fallback: string): string => {
    if (typeof err === "object" && err !== null && "response" in err) {
      const response = (err as { response?: { data?: unknown } }).response
        ?.data;

      if (typeof response === "object" && response !== null) {
        const data = response as Record<string, unknown>;

        for (const key of ["detail", "error_message", "message"]) {
          if (typeof data[key] === "string" && data[key]) {
            return data[key] as string;
          }
        }
      }
    }

    return err instanceof Error ? err.message : fallback;
  };

  const selectedModel = computed(
    () =>
      models.value.find((model) => model.id === selectedModelId.value) ?? null,
  );

  const evaluation = computed(() => modelState.value?.evaluation ?? null);
  const training = computed(() => modelState.value?.training ?? null);

  const evaluationAvailable = computed(
    () =>
      training.value?.status === "COMPLETED" &&
      evaluation.value?.accuracy != null,
  );

  const summaryCards = computed(() => {
    const metrics = evaluation.value;

    const formatPercent = (value: number | null | undefined) =>
      value == null ? "—" : `${(value * 100).toFixed(1)}%`;

    return [
      {
        label: "ACCURACY",
        value: formatPercent(metrics?.accuracy),
        description: "Correct predictions on the held-out test set",
      },
      {
        label: "BALANCED ACCURACY",
        value: formatPercent(metrics?.balanced_accuracy),
        description: "Average recall across classes",
      },
      {
        label: "PRECISION",
        value: formatPercent(metrics?.precision),
        description: "Precision reported by the training evaluation",
      },
      {
        label: "F1 SCORE",
        value: formatPercent(metrics?.f1),
        description: "F1 reported by the training evaluation",
      },
    ];
  });

  const selectModel = async (id: number) => {
    if (selectedModelId.value === id && modelState.value?.id === id) {
      return;
    }

    selectedModelId.value = id;
    modelState.value = null;
    isStateLoading.value = true;
    error.value = null;

    try {
      modelState.value = await modelService.getModelState(id);
    } catch (err: unknown) {
      error.value = messageFromError(
        err,
        "Failed to load evaluation results for this model.",
      );
    } finally {
      isStateLoading.value = false;
    }
  };

  const fetchModels = async () => {
    isLoading.value = true;
    error.value = null;

    try {
      models.value = (await modelService.getModels()).filter(
        (model) =>
          model.prediction_target === "knee_alignment" &&
          model.feature_schema_version === "fppa_v2",
      );

      if (!models.value.length) {
        selectedModelId.value = null;
        modelState.value = null;
        return;
      }

      const initialModel =
        models.value.find((model) => model.is_active) ?? models.value[0];

      await selectModel(initialModel.id);
    } catch (err: unknown) {
      error.value = messageFromError(err, "Failed to load the Model Registry.");
    } finally {
      isLoading.value = false;
    }
  };

  const formatPercent = (value: number | null | undefined) =>
    value == null ? "—" : `${(value * 100).toFixed(1)}%`;

  const formatDate = (value: string | null | undefined) => {
    if (!value) return "—";

    const date = new Date(value);

    return Number.isNaN(date.getTime())
      ? "—"
      : new Intl.DateTimeFormat(undefined, {
          dateStyle: "medium",
          timeStyle: "short",
        }).format(date);
  };

  const formatAngle = (value: string | null | undefined) => {
    if (!value) return "Not specified";

    return value.charAt(0).toUpperCase() + value.slice(1);
  };

  const formatTarget = (value: string | null | undefined) => {
    return value === "knee_alignment"
      ? "Frontal-plane knee alignment"
      : "Unsupported model setup";
  };

  onMounted(fetchModels);

  return {
    models,
    selectedModel,
    selectedModelId,
    modelState,
    evaluation,
    training,
    summaryCards,
    evaluationAvailable,
    isLoading,
    isStateLoading,
    error,
    selectModel,
    fetchModels,
    formatPercent,
    formatDate,
    formatAngle,
    formatTarget,
  };
}
