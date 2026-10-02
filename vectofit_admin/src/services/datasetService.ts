import client from "../config/client";

export interface CreateDatasetPayload {
  name: string;
  description?: string;
  exercise_type: string;
  purpose: string;
  primary_target: string;
  secondary_target?: string;
  created_at: string;
  video_file: File | null;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  created_at: string;
  sample_count: number;
  status: "PENDING" | "PROCESSING" | "READY" | "FAILED";
  video_file: string | null;
}

export const datasetService = {
  async getDatasets(): Promise<Dataset[]> {
    const response = await client.get<Dataset[]>("/datasets/");
    return response.data;
  },

  async createDatasetWithVideo(
    payload: CreateDatasetPayload | FormData,
  ): Promise<Dataset> {
    const response = await client.post<Dataset>("/datasets/", payload, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },
};
