import { computed, ref } from "vue";
import {
  experimentService,
  type ExperimentResultsResponse,
  type ReadinessReport,
} from "../services/experimentService";

export function useExperimentReadiness() {
  const datasetIdsText = ref("17");
  const viewAngle = ref("frontal");
  const report = ref<ReadinessReport | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const participantsWithBad = computed(
    () => report.value?.participants.filter((p) => p.bad > 0).length ?? 0,
  );
  const fragileParticipants = computed(
    () =>
      report.value?.participants
        .filter((p) => p.bad === 1 || p.good === 1)
        .map((p) => p.code) ?? [],
  );

  const load = async () => {
    const ids = datasetIdsText.value
      .split(",")
      .map((part) => Number(part.trim()))
      .filter((n) => Number.isInteger(n) && n > 0);
    if (!ids.length) {
      error.value = "Enter at least one dataset ID.";
      return;
    }
    isLoading.value = true;
    error.value = null;
    try {
      report.value = await experimentService.getReadiness(ids, viewAngle.value);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      error.value = detail ?? "Couldn't load readiness for these datasets.";
      report.value = null;
    } finally {
      isLoading.value = false;
    }
  };

  return {
    datasetIdsText,
    viewAngle,
    report,
    isLoading,
    error,
    participantsWithBad,
    fragileParticipants,
    load,
  };
}

export function useExperimentResults() {
  const bundle = ref<"main" | "demo">("main");
  const response = ref<ExperimentResultsResponse | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const load = async () => {
    isLoading.value = true;
    error.value = null;
    try {
      response.value = await experimentService.getResults(bundle.value);
    } catch {
      error.value = "Couldn't load the experiment bundle.";
      response.value = null;
    } finally {
      isLoading.value = false;
    }
  };

  return { bundle, response, isLoading, error, load };
}
