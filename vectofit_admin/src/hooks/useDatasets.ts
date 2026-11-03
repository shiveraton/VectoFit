import { ref, computed, watch, onUnmounted } from "vue";
import {
  datasetService,
  type Dataset,
  type Participant,
  type CreateDatasetPayload,
} from "../services/datasetService";

export function useDatasets() {
  const datasets = ref<Dataset[]>([]);
  const participants = ref<Participant[]>([]);

  const isLoading = ref(false);
  const isRefreshing = ref(false);
  const isInitialized = ref(false);
  const isCreating = ref(false);
  const isModalOpen = ref(false);

  const errorMessage = ref("");
  const successMessage = ref("");

  const isPolling = ref(false);

  const datasetForm = ref<CreateDatasetPayload>({
    name: "",
    description: "",
    participant: 0,
    exercise_type: "bodyweight_squat",
    purpose: "training",
    primary_target: "squat_quality",
    secondary_target: "biomechanical_errors",
    view_angle: null,
    video_file: null,
  });

  const fetchDatasets = async (force = false) => {
    if (isInitialized.value && !force) {
      return;
    }

    if (force) {
      isRefreshing.value = true;
    } else {
      isLoading.value = true;
    }

    try {
      datasets.value = await datasetService.getDatasets();
      isInitialized.value = true;
    } catch (error) {
      console.error("Failed to load datasets:", error);
      errorMessage.value = "Unable to load datasets.";

      if (!isInitialized.value) {
        isInitialized.value = false;
      }
    } finally {
      if (force) {
        isRefreshing.value = false;
      } else {
        isLoading.value = false;
      }
    }
  };

  const fetchParticipants = async () => {
    try {
      participants.value = await datasetService.getParticipants();
    } catch (error) {
      console.error("Failed to load participants:", error);
      errorMessage.value = "Unable to load participants.";
    }
  };

  const refreshDatasets = () => fetchDatasets(true);

  let processingPollInterval: ReturnType<typeof setInterval> | null = null;

  const stopProcessingPolling = () => {
    if (processingPollInterval !== null) {
      clearInterval(processingPollInterval);
      processingPollInterval = null;
    }
  };

  const pollProcessingState = async () => {
    const hasProcessingDatasets = datasets.value.some(
      (dataset) => dataset.status === "PROCESSING",
    );

    if (!hasProcessingDatasets) {
      stopProcessingPolling();
      return;
    }

    try {
      await fetchDatasets(true);
    } catch (error) {
      console.error("Failed to poll dataset processing state:", error);
    }
  };

  const startProcessingPolling = () => {
    if (processingPollInterval !== null) {
      return;
    }

    processingPollInterval = setInterval(() => {
      void pollProcessingState();
    }, 3000);
  };

  watch(
    () => datasets.value.some((dataset) => dataset.status === "PROCESSING"),
    (hasProcessingDatasets) => {
      if (hasProcessingDatasets) {
        startProcessingPolling();
      } else {
        stopProcessingPolling();
      }
    },
  );

  onUnmounted(() => {
    stopProcessingPolling();
  });

  const resetDatasetForm = () => {
    datasetForm.value = {
      name: "",
      description: "",
      participant: 0,
      exercise_type: "bodyweight_squat",
      purpose: "training",
      primary_target: "squat_quality",
      secondary_target: "biomechanical_errors",
      view_angle: null,
      video_file: null,
    };
  };

  const openCreateModal = () => {
    resetDatasetForm();

    errorMessage.value = "";
    successMessage.value = "";

    isModalOpen.value = true;
  };

  const closeCreateModal = () => {
    if (isCreating.value) {
      return;
    }

    isModalOpen.value = false;
  };

  const handleCreateDataset = async () => {
    if (!datasetForm.value.name.trim()) {
      errorMessage.value = "Dataset name is required.";
      return false;
    }

    if (!datasetForm.value.video_file) {
      errorMessage.value = "Please select a video.";
      return false;
    }

    if (!datasetForm.value.participant) {
      errorMessage.value = "Please assign a participant.";
      return false;
    }

    isCreating.value = true;
    errorMessage.value = "";
    successMessage.value = "";

    try {
      const formData = new FormData();

      formData.append("name", datasetForm.value.name.trim());

      if (datasetForm.value.description) {
        formData.append("description", datasetForm.value.description);
      }

      formData.append("exercise_type", datasetForm.value.exercise_type);
      formData.append("purpose", datasetForm.value.purpose);
      formData.append("primary_target", datasetForm.value.primary_target);
      formData.append("participant", String(datasetForm.value.participant));

      if (datasetForm.value.secondary_target) {
        formData.append("secondary_target", datasetForm.value.secondary_target);
      }

      if (datasetForm.value.view_angle !== null) {
        formData.append("view_angle", String(datasetForm.value.view_angle));
      }

      formData.append("video_file", datasetForm.value.video_file);

      await datasetService.createDatasetWithVideo(formData);

      successMessage.value = "Dataset created successfully.";

      resetDatasetForm();
      isModalOpen.value = false;

      await refreshDatasets();

      return true;
    } catch (error: any) {
      console.error("Failed to create dataset:", error);
      console.error(
        "Backend response:",
        JSON.stringify(error?.response?.data, null, 2),
      );

      errorMessage.value =
        JSON.stringify(error?.response?.data) || "Failed to create dataset.";

      return false;
    } finally {
      isCreating.value = false;
    }
  };

  const retryDataset = async (id: number) => {
    errorMessage.value = "";
    successMessage.value = "";

    try {
      await datasetService.retryDataset(id);

      successMessage.value = "Dataset processing restarted.";

      await refreshDatasets();

      return true;
    } catch (error: any) {
      console.error("Failed to retry dataset:", error);
      console.error(
        "Backend response:",
        JSON.stringify(error?.response?.data, null, 2),
      );

      errorMessage.value =
        JSON.stringify(error?.response?.data) || "Failed to retry dataset.";

      return false;
    }
  };

  const totalDatasets = computed(() => datasets.value.length);

  const totalSamples = computed(() =>
    datasets.value.reduce(
      (total, dataset) => total + (dataset.sample_count || 0),
      0,
    ),
  );

  const totalCorrect = computed(() =>
    datasets.value.reduce((total) => total + 0, 0),
  );

  const totalIncorrect = computed(() => 0);

  const usableDatasets = computed(() =>
    datasets.value.filter((dataset) => dataset.is_usable_for_training),
  );

  onUnmounted(() => {
    stopProcessingPolling();
  });

  return {
    datasets,
    participants,
    isLoading,
    isInitialized,
    isCreating,
    isModalOpen,
    isPolling,
    datasetForm,
    errorMessage,
    successMessage,

    totalDatasets,
    totalSamples,
    totalCorrect,
    totalIncorrect,
    usableDatasets,

    fetchDatasets,
    fetchParticipants,
    refreshDatasets,
    retryDataset,

    startProcessingPolling,
    stopProcessingPolling,

    openCreateModal,
    closeCreateModal,
    handleCreateDataset,
  };
}
