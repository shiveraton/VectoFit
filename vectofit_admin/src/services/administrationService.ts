import client from "../config/client";
import type { CurrentUser } from "./accountService";

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AdminUser extends CurrentUser {
  is_staff: boolean;
  is_validator: boolean;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
}

export interface ActivityEntry {
  id: number;
  actor_username: string;
  action: string;
  action_label: string;
  details: string;
  created_at: string;
}

export const administrationService = {
  async getUsers(page: number, search: string): Promise<Page<AdminUser>> {
    const response = await client.get<Page<AdminUser>>("/accounts/users/", { params: { page, search } });
    return response.data;
  },
  async getActivity(page: number, search: string, action: string): Promise<Page<ActivityEntry>> {
    const response = await client.get<Page<ActivityEntry>>("/accounts/activity-logs/", { params: { page, search, action } });
    return response.data;
  },
};
