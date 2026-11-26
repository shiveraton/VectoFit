import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { inferenceService, type InferenceStatus } from "../services/inferenceService";
import { modelService } from "../services/modelService";
import { queryKeys } from "../query";
import { trainingErrorMessage } from "./errors";

function isInferenceActive(status?: InferenceStatus) {
  return status === "PENDING" || status === "PROCESSING";
}

export function useInferenceLab() {
  const cache = useQueryClient();
  const [modelId, setModelId] = useState<number | null>(null);
  const [simulationId, setSimulationId] = useState<number | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [page, setPage] = useState(1);
  const modelsQuery = useQuery({ queryKey: queryKeys.models, queryFn: modelService.getModels });
  const models = (modelsQuery.data ?? []).filter((model) =>
    model.view_angle === "frontal" && model.prediction_target === "knee_alignment" && model.feature_schema_version === "fppa_v2",
  );
  const model = useQuery({
    queryKey: queryKeys.model(modelId ?? 0),
    queryFn: () => modelService.getModelState(modelId!),
    enabled: modelId !== null,
  });
  const history = useQuery({
    queryKey: queryKeys.inferenceHistory(page),
    queryFn: () => inferenceService.getSimulations(page),
    refetchInterval: (query) => query.state.data?.results.some((item) => isInferenceActive(item.status)) ? 3000 : false,
  });
  const detail = useQuery({
    queryKey: queryKeys.inferenceSimulation(simulationId ?? 0),
    queryFn: () => inferenceService.getSimulation(simulationId!),
    enabled: simulationId !== null,
    refetchInterval: (query) => {
      const simulation = query.state.data;
      return simulation && (isInferenceActive(simulation.status) || simulation.runs.some((run) => isInferenceActive(run.status))) ? 3000 : false;
    },
  });
  const invalidateHistory = () => cache.invalidateQueries({ queryKey: ["inference-history"] });
  const upload = useMutation({
    mutationFn: ({ video, selectedModel }: { video: File; selectedModel: number }) => inferenceService.createSimulation(video, selectedModel),
    onSuccess: async (simulation) => {
      cache.setQueryData(queryKeys.inferenceSimulation(simulation.id), simulation);
      setSimulationId(simulation.id);
      setFile(null);
      setPage(1);
      await invalidateHistory();
    },
  });
  const run = useMutation({
    mutationFn: ({ id, selectedModel }: { id: number; selectedModel: number }) => inferenceService.runModel(id, selectedModel),
    onSuccess: async (_, { id }) => {
      await cache.invalidateQueries({ queryKey: queryKeys.inferenceSimulation(id) });
    },
  });
  const remove = useMutation({
    mutationFn: inferenceService.deleteSimulation,
    onSuccess: async (_, id) => {
      cache.removeQueries({ queryKey: queryKeys.inferenceSimulation(id) });
      setSimulationId(null);
      setPage(1);
      await invalidateHistory();
    },
  });
  const simulation = detail.data;
  const active = Boolean(simulation && (isInferenceActive(simulation.status) || simulation.runs.some((item) => isInferenceActive(item.status))));
  const runStatuses = simulation?.runs.map((item) => item.status).join(",");
  useEffect(() => {
    if (simulationId !== null) void cache.invalidateQueries({ queryKey: ["inference-history"] });
  }, [simulationId, simulation?.status, runStatuses, cache]);
  const existingRun = simulation?.runs.find((item) => item.model === modelId);
  const modelReady = model.data?.artifact_available && model.data.training.status === "COMPLETED";
  const pending = upload.isPending || run.isPending || remove.isPending;
  const canRun = Boolean(modelId && modelReady && !active && !pending && (file || simulation) && existingRun?.status !== "COMPLETED");
  const error = upload.error ?? run.error ?? remove.error ?? detail.error ?? history.error ?? modelsQuery.error ?? model.error;
  return {
    models, model, modelId, setModelId, file, setFile, page, setPage, history, detail,
    simulation, simulationId, active, pending, canRun, existingRun,
    isLoadingModels: modelsQuery.isPending,
    error: error ? trainingErrorMessage(error, "Inference request failed.") : null,
    selectSimulation: (id: number | null) => {
      upload.reset();
      run.reset();
      remove.reset();
      setFile(null);
      setSimulationId(id);
    },
    start: () => {
      if (!canRun || modelId === null) return;
      if (file) upload.mutate({ video: file, selectedModel: modelId });
      else if (simulationId !== null) run.mutate({ id: simulationId, selectedModel: modelId });
    },
    remove: () => { if (simulationId !== null) remove.mutate(simulationId); },
  };
}
