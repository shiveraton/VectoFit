import { useSearchParams } from "react-router";
import axios from "axios";
import { useEffect, useRef } from "react";
import { create } from "zustand";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { trainingService, type TrainingJob } from "../services/trainingService";
import { datasetService, type ViewAngle } from "../services/datasetService";
import { queryKeys } from "../query";
import { trainingErrorMessage } from "./errors";
import type { TrainingSplit } from "../services/trainingService";
export type { ViewAngle } from "../services/datasetService";

interface TrainingDraft {
  selectedDatasetIds: number[];
  selectedViewAngle: ViewAngle | null;
  selectedFeatureIds: string[];
  selectedAlgorithmId: string;
  hyperparameters: Record<string, unknown>;
  selectedJobId: number | null;
  trainingSplit: TrainingSplit;
  testSize: number;
}
const useDraft = create<TrainingDraft>(() => ({
  selectedDatasetIds: [],
  selectedViewAngle: "frontal",
  selectedFeatureIds: trainingService.getAvailableFeatures().map((feature) => feature.id),
  selectedAlgorithmId: "xgboost",
  hyperparameters: {},
  selectedJobId: null,
  trainingSplit: "holdout",
  testSize: 0.3,
}));
export function useTraining() {
  const cache = useQueryClient();
  const [searchParams] = useSearchParams();
  const requestedJobId = Number(searchParams.get("job"));
  useEffect(() => {
    if (Number.isInteger(requestedJobId) && requestedJobId > 0) {
      useDraft.setState({ selectedJobId: requestedJobId });
    }
  }, [requestedJobId]);
  const draft = useDraft();
  const jobs = useQuery({
    queryKey: queryKeys.training,
    queryFn: trainingService.getTrainingJobs,
    refetchInterval: (query) =>
      query.state.data?.some((job) =>
        ["PENDING", "RUNNING"].includes(job.status),
      )
        ? 3000
        : false,
  });
  const data = useQuery({
    queryKey: queryKeys.datasets,
    queryFn: datasetService.getDatasets,
  });
  const trainingJobs = (jobs.data ?? []).filter(
    (job) =>
      job.prediction_target === "knee_alignment" &&
      job.feature_schema_version === "fppa_v2",
  );
  const previous = useRef(new Map<number, string>());
  useEffect(() => {
    if (
      trainingJobs.some(
        (job) =>
          job.status === "COMPLETED" &&
          previous.current.get(job.id) !== "COMPLETED",
      )
    )
      void cache.invalidateQueries({ queryKey: queryKeys.models });
    previous.current = new Map(trainingJobs.map((job) => [job.id, job.status]));
  }, [jobs.data, cache]);
  const start = useMutation({
    mutationFn: trainingService.startTraining,
    onError: (error) => {
      const response: unknown = axios.isAxiosError(error)
        ? error.response?.data
        : undefined;
      if (
        response &&
        typeof response === "object" &&
        "id" in response &&
        typeof response.id === "number" &&
        "status" in response &&
        typeof response.status === "string"
      ) {
        const failed = response as TrainingJob;
        cache.setQueryData<TrainingJob[]>(queryKeys.training, (previous) => [
          failed,
          ...(previous ?? []).filter((item) => item.id !== failed.id),
        ]);
      }
    },
    onSuccess: async (job) => {
      cache.setQueryData<TrainingJob[]>(queryKeys.training, (old) => [
        job,
        ...(old ?? []).filter((item) => item.id !== job.id),
      ]);
      useDraft.setState({ selectedJobId: job.id });
      await cache.invalidateQueries({ queryKey: queryKeys.training });
      if (job.status === "COMPLETED")
        await cache.invalidateQueries({ queryKey: queryKeys.models });
    },
  });
  const datasets = data.data ?? [];
  const features = trainingService.getAvailableFeatures().map((feature) => ({
    ...feature,
    selected: draft.selectedFeatureIds.includes(feature.id),
  }));
  const algorithms = trainingService.getAvailableAlgorithms();
  const selectedDatasets = datasets.filter((dataset) =>
    draft.selectedDatasetIds.includes(dataset.id),
  );
  const availableDatasets = datasets.filter(
    (dataset) => dataset.status === "READY" && dataset.purpose === "training",
  );
  const filteredDatasets = availableDatasets.filter(
    (dataset) =>
      draft.selectedViewAngle &&
      (dataset.view_angles ?? []).includes(draft.selectedViewAngle),
  );
  const activeJobs = trainingJobs.filter((job) =>
    ["PENDING", "RUNNING"].includes(job.status),
  );
  const completedJobs = trainingJobs.filter(
    (job) => job.status === "COMPLETED",
  );
  const isTraining = start.isPending || activeJobs.length > 0;
  const selectedFeatures = features.filter((feature) => feature.selected);
  const selectedAlgorithm =
    algorithms.find(
      (algorithm) => algorithm.id === draft.selectedAlgorithmId,
    ) ?? null;
  const canStartTraining =
    draft.selectedDatasetIds.length > 0 &&
    draft.selectedViewAngle !== null &&
    selectedFeatures.length > 0 &&
    selectedAlgorithm !== null &&
    !isTraining;
  const summaryCards = [
    {
      label: "Total Runs",
      value: trainingJobs.length,
      description: "FPPA v2 knee-alignment experiments",
      icon: "R",
      variant: "samples" as const,
    },
    {
      label: "Completed Runs",
      value: completedJobs.length,
      description: "Completed FPPA runs",
      icon: "C",
      variant: "correct" as const,
    },
    {
      label: "Active Jobs",
      value: activeJobs.length,
      description: "Pending or running jobs",
      icon: "T",
      variant: "samples" as const,
    },
    {
      label: "Failed Runs",
      value: trainingJobs.filter((job) => job.status === "FAILED").length,
      description: "Experiments that ended with errors",
      icon: "F",
      variant: "incorrect" as const,
    },
  ];
  return {
    ...draft,
    datasets,
    features,
    algorithms,
    selectedDatasets,
    availableDatasets,
    filteredDatasets,
    trainingJobs,
    selectedJob:
      trainingJobs.find((job) => job.id === draft.selectedJobId) ??
      trainingJobs[0] ??
      null,
    summaryCards,
    configSummaryText: `${draft.selectedDatasetIds.length ? `${draft.selectedDatasetIds.length} dataset(s)` : "No datasets"} · frontal view · FPPA knee alignment · ${selectedFeatures.length} selected FPPA features · XGBoost`,
    canStartTraining,
    isLoading: jobs.isPending || data.isPending,
    isTraining,
    error: start.error
      ? trainingErrorMessage(
          start.error,
          "An unexpected error occurred during training.",
        )
      : jobs.error || data.error
        ? trainingErrorMessage(
            jobs.error ?? data.error,
            "An unexpected error occurred during training.",
          )
        : null,
    fetchTrainingData: async (_force = false) =>
      Promise.all([jobs.refetch(), data.refetch()]),
    selectJob: (selectedJobId: number) => useDraft.setState({ selectedJobId }),
    toggleDataset: (id: number) =>
      useDraft.setState((state) => ({
        selectedDatasetIds: state.selectedDatasetIds.includes(id)
          ? state.selectedDatasetIds.filter((item) => item !== id)
          : [...state.selectedDatasetIds, id],
      })),
    toggleFeature: (id: string) => {
      if (isTraining || !features.some((feature) => feature.id === id)) return;
      useDraft.setState((state) => ({
        selectedFeatureIds: state.selectedFeatureIds.includes(id)
          ? state.selectedFeatureIds.filter((item) => item !== id)
          : [...state.selectedFeatureIds, id],
      }));
    },
    setHyperparameter: (name: string, value: unknown) =>
      useDraft.setState((state) => ({
        hyperparameters: { ...state.hyperparameters, [name]: value },
      })),
    setTrainingSplit: (trainingSplit: TrainingSplit) =>
      useDraft.setState({ trainingSplit }),
    setTestSize: (testSize: number) => useDraft.setState({ testSize }),
    startTraining: async () => {
      if (!canStartTraining || !selectedAlgorithm || !draft.selectedViewAngle)
        return null;
      try {
        return await start.mutateAsync({
          dataset_ids: draft.selectedDatasetIds,
          algorithm: selectedAlgorithm.id,
          view_angle: draft.selectedViewAngle,
          prediction_target: "knee_alignment",
          feature_selection: selectedFeatures.map((feature) => feature.id),
          hyperparameters: draft.hyperparameters,
          split_strategy: draft.trainingSplit,
          ...(draft.trainingSplit === "holdout"
            ? { test_size: draft.testSize }
            : {}),
        });
      } catch {
        return null;
      }
    },
  };
}
