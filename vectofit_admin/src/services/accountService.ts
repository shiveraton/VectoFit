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
