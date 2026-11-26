import apiClient from "../../../api/client";
import type { SessionResult } from "../model/types";
import { assertSessionResult } from "../model/validation";

export interface LiveSession {
  id: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  view_angle: string;
  session_result?: SessionResult | null;
  session_saved?: boolean;
}

export async function getLiveSession(id: number, signal?: AbortSignal): Promise<LiveSession> {
  const response = await apiClient.get<LiveSession>(`/assessments/sessions/${id}/`, { params: { include: "reps" }, signal });
  if (response.data.session_result) {
    if (response.data.session_result.sessionId !== String(id)) throw new Error("Session identity mismatch.");
    assertSessionResult(response.data.session_result);
  }
  return response.data;
}

export async function retryLiveSession(id: number): Promise<LiveSession> {
  const response = await apiClient.post<LiveSession>(`/assessments/sessions/${id}/retry/`);
  return response.data;
}
