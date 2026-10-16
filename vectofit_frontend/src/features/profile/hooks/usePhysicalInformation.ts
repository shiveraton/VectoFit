import { useCallback, useEffect, useState } from "react";
import axios from "axios";

import {
  getCurrentProfile,
  updatePhysicalInformation,
  type PhysicalInformationPayload,
} from "../services/profileService";

export default function usePhysicalInformation() {
  const [weight, setWeight] = useState<number | null>(null);
  const [height, setHeight] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    setIsLoading(true);

    try {
      const profile = await getCurrentProfile();

      setWeight(profile.weight_kg);
      setHeight(profile.height_cm);
    } catch (error) {
      if (axios.isAxiosError(error)) {
        console.error(
          "Profile request failed:",
          error.response?.status,
          error.response?.data,
        );
        console.error("Request URL:", error.config?.url);
        console.error("Base URL:", error.config?.baseURL);
      } else {
        console.error("Failed to load profile:", error);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  const savePhysicalInformation = useCallback(
    async (payload: PhysicalInformationPayload): Promise<void> => {
      const profile = await updatePhysicalInformation(payload);

      setWeight(profile.weight_kg);
      setHeight(profile.height_cm);
    },
    [],
  );

  return {
    weight,
    height,
    isLoading,
    savePhysicalInformation,
  };
}
