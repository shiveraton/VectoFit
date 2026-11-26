import client from "../config/client";

export type InferenceStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface InferenceRepetition {
  rep_number: number;
  start_ms: number;
  end_ms: number;
  valid: boolean;
  reason: string | null;
  features: Record<string, number>;
}

export interface InferencePrediction {
  rep_number: number;
  status: string;
  reason?: string;
  predicted_class?: string;
  probability?: number | null;
  inference_ms?: number;
}

export interface InferenceRun {
  id: number;
  model: number | null;
  model_snapshot: { id: number; name: string; version: string; features: string[] };
  status: InferenceStatus;
  error_message: string;
  predictions: InferencePrediction[];
  model_loading_ms: number | null;
  inference_ms: number | null;
}

export interface InferenceHistoryItem {
  id: number;
  original_filename: string;
  status: InferenceStatus;
  error_message: string;
  created_at: string;
}

export interface InferenceSimulation extends InferenceHistoryItem {
  repetitions: InferenceRepetition[];
  runs: InferenceRun[];
  preprocessing_ms: number | null;
}

export interface InferenceHistory {
  count: number;
  next: string | null;
  previous: string | null;
  results: InferenceHistoryItem[];
}

const base = "/training/inference-simulations/";
export const inferenceService = {
  async getSimulations(page: number) {
    return (await client.get<InferenceHistory>(base, { params: { page } })).data;
  },
  async getSimulation(id: number) {
    return (await client.get<InferenceSimulation>(`${base}${id}/`)).data;
  },
  async createSimulation(file: File, modelId: number) {
    const body = new FormData();
    body.append("video_file", file);
    body.append("model_id", String(modelId));
    return (await client.post<InferenceSimulation>(base, body)).data;
  },
  async runModel(id: number, modelId: number) {
    return (await client.post<InferenceRun>(`${base}${id}/runs/`, { model_id: modelId })).data;
  },
  async deleteSimulation(id: number) {
    await client.delete(`${base}${id}/`);
  },
  async getVideo(id: number, signal: AbortSignal): Promise<Blob> {
    return (await client.get<Blob>(`${base}${id}/video/`, { responseType: "blob", signal })).data;
  },
};
