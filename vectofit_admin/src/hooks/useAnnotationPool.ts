import { computed, ref } from "vue";
import {
  annotationPoolService,
  type AnnotationPoolJob,
} from "../services/annotationPoolService";

export function useAnnotationPool() {
  const jobs = ref<AnnotationPoolJob[]>([]);
  const selectedJobId = ref<number | null>(null);
  const search = ref("");
  const statusFilter = ref("ALL");
  const isLoading = ref(false);
  const error = ref("");

  const selectedJob = computed(
    () => jobs.value.find((job) => job.id === selectedJobId.value) ?? null,
  );

  const filteredJobs = computed(() => {
    const query = search.value.trim().toLowerCase();

    return jobs.value.filter((job) => {
      const matchesSearch =
        !query ||
        job.name.toLowerCase().includes(query) ||
        job.annotators.some((summary) =>
          summary.annotator?.username.toLowerCase().includes(query),
        );
      const matchesStatus =
        statusFilter.value === "ALL" ||
        job.job_status === statusFilter.value;

      return matchesSearch && matchesStatus;
    });
  });

  const fetchJobs = async () => {
    isLoading.value = true;
    error.value = "";

    try {
      jobs.value = await annotationPoolService.getJobs();

      if (
        selectedJobId.value !== null &&
        !jobs.value.some((job) => job.id === selectedJobId.value)
      ) {
        selectedJobId.value = null;
      }
    } catch (requestError) {
      console.error("Failed to load annotation pool:", requestError);
      error.value = "Unable to load annotation activity.";
    } finally {
      isLoading.value = false;
    }
  };

  const selectJob = (job: AnnotationPoolJob) => {
    selectedJobId.value = job.id;
  };

  const clearSelection = () => {
    selectedJobId.value = null;
  };

  return {
    jobs,
    filteredJobs,
    selectedJob,
    search,
    statusFilter,
    isLoading,
    error,
    fetchJobs,
    selectJob,
    clearSelection,
  };
}
