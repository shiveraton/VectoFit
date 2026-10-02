export type DeploymentStatus = "inactive" | "building" | "active" | "failed";
export type Environment = "staging" | "production";

export interface ModelVersion {
  id: string;
  version: string;
  createdAt: string;
  gitCommit: string;
  trainingJobId: string;
  artifactUri: string;
  accuracy: number;
  latencyMs: number;
  status: DeploymentStatus;
  environment?: Environment;
  endpointUrl?: string;
}

export interface Model {
  id: string;
  name: string;
  description: string;
  framework: string;
  updatedAt: string;
  versions: ModelVersion[];
}

export interface DeployPayload {
  modelId: string;
  versionId: string;
  environment: Environment;
  minReplicas: number;
  maxReplicas: number;
}

export interface SummaryCardData {
  readonly label: string;
  readonly value: string | number;
  readonly description: string;
  readonly icon: string;
  readonly variant?: "samples" | "incorrect" | "correct" | "version";
}

export const modelService = {
  async getModels(): Promise<Model[]> {
    const response = await fetch("/api/v1/models");
    if (!response.ok) {
      throw new Error("Failed to fetch model registry");
    }
    return response.json();
  },

  async deployVersion(payload: DeployPayload): Promise<void> {
    const response = await fetch(`/api/v1/models/${payload.modelId}/deploy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error("Deployment failed");
    }
  },

  async undeployVersion(modelId: string, versionId: string): Promise<void> {
    const response = await fetch(
      `/api/v1/models/${modelId}/versions/${versionId}/undeploy`,
      {
        method: "POST",
      },
    );
    if (!response.ok) {
      throw new Error("Undeployment failed");
    }
  },
};
