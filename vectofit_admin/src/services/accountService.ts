import client from "../config/client";

export interface CurrentUser {
  id: number;
  username: string;
  email: string;
  is_annotator: boolean;
}

export const accountService = {
  async getCurrentUser(): Promise<CurrentUser> {
    const response = await client.get<CurrentUser>("/accounts/me/");
    return response.data;
  },

  async updateCurrentUser(id: number, changes: Pick<CurrentUser, "username" | "email">): Promise<CurrentUser> {
    const response = await client.patch<CurrentUser>(`/accounts/me/${id}/`, changes);
    return response.data;
  },

  async register(payload: {
    username: string;
    email: string;
    password: string;
    confirm_password: string;
    is_annotator: boolean;
  }): Promise<void> {
    await client.post("/accounts/register/", payload);
  },
};
