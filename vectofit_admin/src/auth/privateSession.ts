import axios from "axios";
import client from "../config/client";
import { accountService } from "../services/accountService";
import { getAuthToken, useAuthStore } from "../state/auth";
import { queryClient } from "../query";

export const privateHome = (isAnnotator: boolean) =>
  isAnnotator ? "/annotator" : "/dashboard";

export function signOut() {
  useAuthStore.getState().logout();
}

useAuthStore.subscribe((state, previous) => {
  if (state.token !== previous.token) {
    void queryClient.cancelQueries();
    queryClient.clear();
  }
});

export async function validatePrivateSession() {
  const token = getAuthToken();
  if (!token) throw new Error("Missing authentication token.");
  try {
    const user = await accountService.getCurrentUser();
    if (getAuthToken() !== token) throw new Error("Session changed.");
    if (!user || typeof user.is_annotator !== "boolean")
      throw new Error("Invalid session response.");
    return user;
  } catch (error: unknown) {
    if (
      axios.isAxiosError(error) &&
      (error.response?.status === 401 || error.response?.status === 403) &&
      getAuthToken() === token
    ) {
      signOut();
    }
    throw error;
  }
}

export async function signIn(identifier: string, password: string) {
  const { data } = await client.post<unknown>("/accounts/login/", {
    identifier,
    password,
  });
  const response =
    typeof data === "object" && data !== null
      ? (data as Record<string, unknown>)
      : {};
  const token = response.access_token || response.token;
  if (typeof token !== "string" || !token.trim())
    throw new Error("Sign-in could not be completed. Please try again.");
  useAuthStore.getState().setToken(token);
  try {
    return await validatePrivateSession();
  } catch (error) {
    if (getAuthToken() === token.trim()) signOut();
    throw error;
  }
}
