import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  annotationPoolService,
  type AnnotationPoolJob,
} from "../services/annotationPoolService";
import { queryKeys } from "../query";
export function useAnnotationPool(enabled = true) {
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const query = useQuery({
    queryKey: queryKeys.annotationPool,
    queryFn: annotationPoolService.getJobs,
    enabled,
    staleTime: 30_000,
  });
  const jobs = query.data ?? [];
  const term = search.trim().toLowerCase();
  const filteredJobs = jobs.filter(
    (job) =>
      (!term ||
        job.name.toLowerCase().includes(term) ||
        job.annotators.some((summary) =>
          summary.annotator?.username.toLowerCase().includes(term),
        )) &&
      (statusFilter === "ALL" || job.job_status === statusFilter),
  );
  return {
    jobs,
    filteredJobs,
    selectedJob: jobs.find((job) => job.id === selectedJobId) ?? null,
    search,
    setSearch,
    statusFilter,
    setStatusFilter,
    isLoading: query.isFetching,
    error: query.error ? "Unable to load annotation activity." : "",
    fetchJobs: () => query.refetch(),
    selectJob: (job: AnnotationPoolJob) => setSelectedJobId(job.id),
    clearSelection: () => setSelectedJobId(null),
  };
}
