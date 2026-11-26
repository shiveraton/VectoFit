import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import useAuthStore from "../../../stores/useAuthStore";
import { getLiveSession, retryLiveSession, type LiveSession } from "../services/sessionResultService";
import type { SessionResultError, SessionResultState } from "../model/types";

export function sessionState(session: LiveSession): SessionResultState {
  if (session.status === "PENDING" || session.status === "PROCESSING") return { status: "loading" };
  if (session.status === "FAILED") return { status: "error", error: { kind: "processing_failed", sessionSaved: session.session_saved === true } };
  if (session.status === "COMPLETED" && session.session_result) return { status: "ready", data: session.session_result };
  return { status: "error", error: { kind: "unknown", detail: session.view_angle !== "frontal"
    ? "Knee-alignment results require a frontal camera view." : "These results are unavailable. Try refreshing this session." } };
}

function requestError(error: unknown): SessionResultError {
  return { kind: isAxiosError(error) && (!error.response || error.response.status >= 500) ? "network" : "unknown" };
}

export default function useSessionResult(id: number) {
  const token = useAuthStore(state => state.token);
  const userId = useAuthStore(state => state.user?.id);
  const cache = useQueryClient();
  const key = ["session-result", userId, id];
  const enabled = Boolean(token) && Number.isInteger(id) && id > 0;
  const query = useQuery({ queryKey: key, queryFn: ({ signal }) => getLiveSession(id, signal), enabled,
    retry: false, staleTime: 0, gcTime: 0,
    refetchInterval: item => item.state.data && ["PENDING", "PROCESSING"].includes(item.state.data.status) ? 3000 : false });
  const reprocess = useMutation({ mutationFn: () => retryLiveSession(id), onSuccess: async session => {
    if (useAuthStore.getState().token !== token) return;
    cache.setQueryData(key, session);
    await query.refetch();
  } });
  let state: SessionResultState = { status: "loading" };
  if (!enabled) state = { status: "error", error: { kind: "unknown", detail: "Sign in to open a valid saved session." } };
  else if (query.isError) state = { status: "error", error: requestError(query.error) };
  else if (query.data) state = sessionState(query.data);
  if (reprocess.isError && query.data?.status === "FAILED") state = { status: "error", error: requestError(reprocess.error) };
  const retry = async () => {
    if (!enabled || query.isFetching || reprocess.isPending) return;
    if (query.data?.status === "FAILED") {
      try { await reprocess.mutateAsync(); }
      catch (error) {
        if (isAxiosError(error) && error.response?.status === 409) { reprocess.reset(); await query.refetch(); }
      }
    } else await query.refetch();
  };
  return { state, retry, retrying: reprocess.isPending || (query.isFetching && query.isError) };
}
