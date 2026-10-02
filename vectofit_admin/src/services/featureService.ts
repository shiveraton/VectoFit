export interface FeatureItem {
  id: string;
  name: string;
  code: string;
  category: string;
  categoryVariant: "orange" | "red" | "warm";
  measurement: string;
  purpose: string;
  icon: string;
}

export interface FeatureGroup {
  id: string;
  icon: string;
  iconVariant: "orange" | "red" | "warm" | "gradient";
  label: string;
  title: string;
  description: string;
  tags: string[];
}

export interface PipelineStep {
  number: string;
  title: string;
  subtitle: string;
}

const CATEGORY_VARIANT_MAP: Record<string, "orange" | "red" | "warm"> = {
  Movement: "orange",
  Velocity: "orange",
  Symmetry: "red",
  Posture: "warm",
  Joint: "warm",
};

export const featureService = {
  async getCoreFeatures(): Promise<FeatureItem[]> {
    const response = await fetch("/api/v1/features");
    if (!response.ok) {
      throw new Error("Failed to fetch feature registry");
    }
    const rawFeatures: Omit<FeatureItem, "categoryVariant">[] =
      await response.json();

    return rawFeatures.map((f) => ({
      ...f,
      categoryVariant: CATEGORY_VARIANT_MAP[f.category] || "warm",
    }));
  },

  async getFeatureGroups(): Promise<FeatureGroup[]> {
    const response = await fetch("/api/v1/feature-groups");
    if (!response.ok) {
      throw new Error("Failed to fetch feature groups");
    }
    return response.json();
  },

  getPipelineSteps(): PipelineStep[] {
    return [
      {
        number: "01",
        title: "Pose Landmarks",
        subtitle: "MediaPipe",
      },
      {
        number: "02",
        title: "Preprocessing",
        subtitle: "Filtering & normalization",
      },
      {
        number: "03",
        title: "Feature Extraction",
        subtitle: "ROM, angles, asymmetry, velocity",
      },
      {
        number: "04",
        title: "Dataset Sample",
        subtitle: "One completed squat rep",
      },
    ];
  },
};
