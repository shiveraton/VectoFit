import apiClient from "../../../api/client";

export interface PhysicalInformationPayload {
  height_cm: number | null;
  weight_kg: number | null;
}

export interface CurrentProfile extends PhysicalInformationPayload {
  username?: string;
  bmi: number | null;
}

function normalizeProfile(data: any): CurrentProfile {
  return {
    username: data.username,
    height_cm: data.height_cm == null ? null : Number(data.height_cm),
    weight_kg: data.weight_kg == null ? null : Number(data.weight_kg),
    bmi: data.bmi == null ? null : Number(data.bmi),
  };
}

export const getProfiles = async () => {
  const response = await apiClient.get("/accounts/profile/");
  return response.data;
};

export const getCurrentProfile = async (): Promise<CurrentProfile> => {
  const response = await apiClient.get("/accounts/profile/current/");
  return normalizeProfile(response.data);
};

export const updatePhysicalInformation = async (
  payload: PhysicalInformationPayload,
): Promise<CurrentProfile> => {
  const response = await apiClient.patch("/accounts/profile/current/", payload);

  return normalizeProfile(response.data);
};
