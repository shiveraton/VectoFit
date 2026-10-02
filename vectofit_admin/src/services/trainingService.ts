export interface TrainingTask {
  id: string;
  code: string;
  title: string;
  description: string;
}

export interface TrainingJob {
  id: string;
  name: string;
  status: "queued" | "running" | "completed" | "failed";
  progressPercentage: number;
  started_at: string;
  tasks?: TrainingTask[];
}

export interface FeatureOption {
  id: string;
  name: string;
  selected: boolean;
}

export interface AlgorithmOption {
  id: string;
  code: string;
  name: string;
  description: string;
}

export interface WorkflowStep {
  number: string;
  title: string;
  subtitle: string;
  active?: boolean;
}

const API_BASE_URL = "/api/v1/training";

export const trainingService = {
  async getTrainingTasks(): Promise<TrainingTask[]> {
    const response = await fetch(`${API_BASE_URL}/tasks`);
    if (!response.ok) {
      throw new Error(
        `Failed to fetch training tasks: ${response.status}${response.statusText}`,
      );
    }
    return response.json();
  },

  async getTrainingJobs(): Promise<TrainingJob[]> {
    const response = await fetch(`${API_BASE_URL}/tasks`);
    if (!response.ok) {
      throw new Error("Failed to fetch training jobs");
    }
    return response.json();
  },

  getAvailableFeatures(): FeatureOption[] {
    return [
      {
        id: "rom",
        name: "ROM",
        selected: true,
      },
      {
        id: "asymmetry",
        name: "Asymmetry",
        selected: true,
      },
      {
        id: "trunk",
        name: "Trunk Angle",
        selected: true,
      },
      {
        id: "knee",
        name: "Knee Angle",
        selected: true,
      },
      {
        id: "hip",
        name: "Hip Angle",
        selected: true,
      },
      {
        id: "velocity",
        name: "Velocity",
        selected: true,
      },
    ];
  },

  async getAlgorithm(): Promise<AlgorithmOption> {
    const response = await fetch(`${API_BASE_URL}/algorithm`);
    if (!response.ok) {
      throw new Error("Failed to fetch default algorithm option");
    }
    return response.json();
  },

  getWorkflowStep(): WorkflowStep[] {
    return [
      {
        number: "01",
        title: "Configure",
        subtitle: "Dataset, task and features",
        active: true,
      },
      {
        number: "02",
        title: "Train",
        subtitle: "Fit the selected model",
      },
      {
        number: "03",
        title: "Evaluate",
        subtitle: "Measure model performance",
      },
      {
        number: "04",
        title: "Register",
        subtitle: "Save the trained model",
      },
    ];
  },
};
