import { ref } from "vue";
import {
  participantService,
  type Participant,
} from "../services/participantService";

export function useParticipants() {
  const participants = ref<Participant[]>([]);

  const isLoading = ref(false);
  const isCreating = ref(false);

  const errorMessage = ref("");
  const successMessage = ref("");

  const fetchParticipants = async () => {
    isLoading.value = true;
    errorMessage.value = "";

    try {
      participants.value = await participantService.getParticipants();
    } catch (error) {
      console.error("Failed to load participants:", error);
      errorMessage.value = "Unable to load participants.";
    } finally {
      isLoading.value = false;
    }
  };

  const createParticipant = async () => {
    isCreating.value = true;
    errorMessage.value = "";
    successMessage.value = "";

    try {
      const participant = await participantService.createParticipant();

      participants.value.push(participant);

      successMessage.value = `Participant ${participant.participant_code} created.`;

      return participant;
    } catch (error: any) {
      console.error("Failed to create participant:", error);

      errorMessage.value =
        error?.response?.data?.detail ||
        error?.response?.data?.participant_code?.[0] ||
        "Failed to create participant.";

      return null;
    } finally {
      isCreating.value = false;
    }
  };

  return {
    participants,
    isLoading,
    isCreating,
    errorMessage,
    successMessage,
    fetchParticipants,
    createParticipant,
  };
}
