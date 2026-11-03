import { ref } from "vue";
import { annotationQueueService, type AnnotationQueueItem } from "../services/annotationQueueService";

export function useAnnotationQueue() {
  const datasets = ref<AnnotationQueueItem[]>([]);
  const isLoading = ref(false);
  const error = ref("");
  const load = async () => {
    isLoading.value = true;
    error.value = "";
    try { datasets.value = await annotationQueueService.list(); }
    catch { error.value = "Unable to load annotation datasets."; }
    finally { isLoading.value = false; }
  };
  return { datasets, isLoading, error, load };
}
