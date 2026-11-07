import client from "../config/client";

export interface Participant {
  id: number;
  participant_code: string;
  created_at: string;
}

export const participantService = {
  async getParticipants(): Promise<Participant[]> {
    const response = await client.get<Participant[]>("/datasets/participant/");

    return response.data;
  },

  async createParticipant(): Promise<Participant> {
    const response = await client.post<Participant>(
      "/datasets/participant/",
      {},
    );

    return response.data;
  },

  async getParticipant(id: number): Promise<Participant> {
    const response = await client.get<Participant>(
      `/datasets/participant/${id}/`,
    );

    return response.data;
  },

  async deleteParticipant(id: number): Promise<void> {
    await client.delete(`/datasets/participant/${id}/`);
  },
};
