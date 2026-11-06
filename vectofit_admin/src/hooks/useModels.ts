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
const isActivatingModel = ref(false);
const activationMessage = ref<string | null>(null);
const isInitialized = ref(false);
const error = ref<string | null>(null);

export const invalidateModels = () => {
  isInitialized.value = false;
};

const messageFromError = (err: unknown, fallback: string): string => {
  const responseData =
    typeof err === "object" && err !== null && "response" in err
      ? (err as { response?: { data?: unknown } }).response?.data
      : undefined;
  if (typeof responseData === "object" && responseData !== null) {
    const data = responseData as Record<string, unknown>;
    for (const key of ["detail", "error_message", "message"]) {
      if (typeof data[key] === "string" && data[key])
        return data[key] as string;
    }
  }
  return err instanceof Error ? err.message : fallback;
};

const fetchModelState = async (id: number) => {
  isStateLoading.value = true;
  error.value = null;

  try {
    modelState.value = await modelService.getModelState(id);
  } catch (err: unknown) {
    error.value = messageFromError(err, "Failed to load model state.");

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
      models.value = (await modelService.getModels()).filter(
        (model) =>
          model.prediction_target === "knee_alignment" &&
          model.feature_schema_version === "fppa_v2",
      );

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
      error.value = messageFromError(err, "Failed to load model registry.");

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

  const activateModel = async (id: number) => {
    isActivatingModel.value = true;
    activationMessage.value = null;
    error.value = null;
    try {
      await modelService.activateModel(id);
      await fetchModels(true);
      selectedModelId.value = id;
      await fetchModelState(id);
      activationMessage.value =
        "Model activated for its camera angle and prediction target.";
    } catch (err: unknown) {
      error.value = messageFromError(err, "Failed to activate model.");
    } finally {
      isActivatingModel.value = false;
    }
  };

  const selectedModel = computed(
    () =>
      models.value.find((model) => model.id === selectedModelId.value) ?? null,
  );

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
          ? "Macro-averaged F1 across good and bad FPPA labels"
          : "No evaluation available",
      },
      {
        label: "FEATURES",
        value: state?.features.selected.length ?? "—",
        description: "Model input features",
      },
    ];
  });

  onMounted(() => fetchModels(true));

  return {
    models,
    modelState,
    selectedModel,
    selectedModelId,
    isLoading,
    isStateLoading,
    isActivatingModel,
    activationMessage,
    isInitialized,
    error,
    summaryCards,
    fetchModels,
    fetchModelState,
    selectModel,
    activateModel,
  };
}
