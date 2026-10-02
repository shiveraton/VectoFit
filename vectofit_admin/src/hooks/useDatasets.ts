import { ref, computed } from "vue";
import {
  datasetService,
  type Dataset,
  type CreateDatasetPayload,
} from "../services/datasetService";

export function useDatasets() {
  const datasets = ref<Dataset[]>([]);
  const isLoading = ref(false);
  const isInitialized = ref<boolean>(false);
  const isCreating = ref(false);
  const isModalOpen = ref(false);
  const errorMessage = ref("");
  const successMessage = ref("");

  const datasetForm = ref<CreateDatasetPayload>({
    name: "",
    description: "",
    exercise_type: "bodyweight_squat",
    purpose: "training",
    primary_target: "squat_quality",
    secondary_target: "biomechanical_errors",
    created_at: "",
    video_file: null,
  });

  const fetchDatasets = async (force = false) => {
    if (isInitialized.value && !force) return;
    isLoading.value = true;
    errorMessage.value = "";
    try {
      datasets.value = await datasetService.getDatasets();
      isInitialized.value = true;
    } catch (error: any) {
      errorMessage.value = "Unable to load datasets.";
    } finally {
      isLoading.value = false;
    }
  };

  const resetDatasetForm = () => {
    datasetForm.value = {
      name: "",
      description: "",
      exercise_type: "bodyweight_squat",
      purpose: "training",
      primary_target: "squat_quality",
      secondary_target: "biomechanical_errors",
      created_at: "",
      video_file: null,
    };
  };

  const openCreateModal = () => {
    datasetForm.value = {
      name: "",
      description: "",
      exercise_type: "bodyweight_squat",
      purpose: "training",
      primary_target: "squat_quality",
      secondary_target: "biomechanical_errors",
      created_at: "",
      video_file: null,
    };
    resetDatasetForm();
    errorMessage.value = "";
    successMessage.value = "";
    isModalOpen.value = true;
  };

  const closeCreateModal = () => {
    isModalOpen.value = false;
  };

  const handleCreateDataset = async () => {
    if (!datasetForm.value.name.trim()) {
      errorMessage.value = "Dataset name is required.";
      return false;
    }

    if (!datasetForm.value.video_file) {
      errorMessage.value = "Please select a video for preprocessing.";
      return false;
    }

    isCreating.value = true;
    errorMessage.value = "";
    successMessage.value = "";

    try {
      const formData = new FormData();
      Object.keys(datasetForm.value).forEach((key) => {
        const val = (datasetForm.value as any)[key];
        if (val !== null) formData.append(key, val);
      });

      await datasetService.createDatasetWithVideo(formData);

      successMessage.value = "Dataset created successfully.";
      resetDatasetForm();
      closeCreateModal();
      await fetchDatasets();
      return true;
    } catch (error: any) {
      errorMessage.value =
        error.response?.data?.detail || "Failed to upload video.";
      return false;
    } finally {
      isCreating.value = false;
    }
  };

  const totalDatasets = computed(() => datasets.value.length);
  const totalSamples = computed(() =>
    datasets.value.reduce((acc, d) => acc + (d.sample_count || 0), 0),
  );

  return {
    datasets,
    isLoading,
    isCreating,
    isModalOpen,
    datasetForm,
    totalDatasets,
    totalSamples,
    errorMessage,
    successMessage,
    fetchDatasets,
    openCreateModal,
    closeCreateModal,
    handleCreateDataset,
  };
}
