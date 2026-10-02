import { ref, computed } from "vue";
import {
  featureService,
  type FeatureItem,
  type FeatureGroup,
  type PipelineStep,
} from "../services/featureService";

const coreFeatures = ref<FeatureItem[]>([]);
const featureGroups = ref<FeatureGroup[]>([]);
const isLoading = ref<boolean>(false);
const isInitialized = ref<boolean>(false);
const error = ref<string | null>(null);

export function useFeatures() {
  const totalFeaturesCount = computed(() => coreFeatures.value.length);
  const totalGroupsCount = computed(() => featureGroups.value.length);

  const fetchFeatures = async (force = false) => {
    if (isInitialized.value && !force) return;

    isLoading.value = true;
    error.value = null;

    try {
      const [featureData, groupsData] = await Promise.all([
        featureService.getCoreFeatures(),
        featureService.getFeatureGroups(),
      ]);

      coreFeatures.value = featureData;
      featureGroups.value = groupsData;
      isInitialized.value = true;
    } catch (err: any) {
      error.value = err.message || "Failed to load feature store registry";
      isInitialized.value = false;
    } finally {
      isLoading.value = false;
    }
  };

  const pipelineSteps = computed<PipelineStep[]>(() => {
    return featureService.getPipelineSteps();
  });

  return {
    coreFeatures,
    featureGroups,
    pipelineSteps,
    isLoading,
    isInitialized,
    error,
    fetchFeatures,
    totalFeaturesCount,
    totalGroupsCount,
  };
}
