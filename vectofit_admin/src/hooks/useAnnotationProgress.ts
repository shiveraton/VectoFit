import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import client from "../config/client";

export function useAnnotationProgress() {
  const totalSamples = ref(0);
  const completedSamples = ref(0);
  const remainingSamples = ref(0);
  const progressPercentage = ref(0);

  const loadProgress = async () => {
    try {
      const response = await client.get("/accounts/me/");
      const user = response.data;

      // Get dataset assignment counts from the annotation-queue endpoint
      const datasetsResponse = await client.get("/annotation-queue/");
      const datasets = datasetsResponse.data || [];

      let total = 0;
      let completed = 0;

      datasets.forEach((dataset: any) => {
        total += dataset.review_total || 0;
        completed += dataset.annotated_by_me || 0;
      });

      totalSamples.value = total;
      completedSamples.value = completed;
      remainingSamples.value = total > 0 ? total - completed : 0;
      progressPercentage.value = total > 0 ? Math.round((completed / total) * 100) : 0;
    } catch (err) {
      console.error("Failed to load progress:", err);
    }
  };

  return {
    totalSamples,
    completedSamples,
    remainingSamples,
    progressPercentage,
    loadProgress,
  };
}