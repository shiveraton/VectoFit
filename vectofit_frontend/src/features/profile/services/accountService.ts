import apiClient from "../../../api/client";

export interface AccountDetails {
  id: number;
  username: string;
  email: string;
}

export async function getCurrentAccount(signal?: AbortSignal): Promise<AccountDetails> {
  const response = await apiClient.get<AccountDetails>("/accounts/me/", { signal });
  return response.data;
}

export async function updateCurrentAccount(
  id: number,
  changes: Pick<AccountDetails, "username" | "email">,
): Promise<AccountDetails> {
  const response = await apiClient.patch<AccountDetails>(`/accounts/me/${id}/`, changes);
  return response.data;
}
