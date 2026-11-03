import { ref, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import client from "../config/client";

export function useAnnotatorDatasets() {
  const datasets = ref([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const fetchDatasets = async () => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await client.get("/annotation-queue/");
      datasets.value = response.data;
    } catch (err) {
      error.value = "Failed to fetch datasets";
      console.error(err);
    } finally {
      isLoading.value = false;
    }
  };

  onMounted(fetchDatasets);

  return {
    datasets,
    isLoading,
    error,
    fetchDatasets,
  };
}