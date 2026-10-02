import { create } from "zustand";
import apiClient from "../api/client";
import { RootStackParamList } from "../navigation/types";

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface RegistrationData {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  login: (identifier: string, password: string) => Promise<void>;
  register: (registrationData: RegistrationData) => Promise<void>;
  logout: () => void;
}

const authStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  setUser: (user) => set({ user }),
  isAuthenticated: false,

  login: async (identifier, password) => {
    const response = await apiClient.post("/accounts/login/", {
      identifier,
      password,
    });

    const token = response.data.token;

    apiClient.defaults.headers.common["Authorization"] = `Token ${token}`;

    const userResponse = await apiClient.get("/accounts/me/");

    set({
      token,
      user: {
        id: userResponse.data.id.toString(),
        email: userResponse.data.email || "",
        name: userResponse.data.username || "",
      },
      isAuthenticated: true,
    });
  },

  register: async (registrationData) => {
    try {
      const response = await apiClient.post(
        "/accounts/register/",
        registrationData,
      );
      return response.data;
    } catch (error: any) {
      const message =
        error.response?.data?.message ||
        error.response?.data?.detail ||
        error.message ||
        "Unknown error";
      console.log("Registration failed:", message);
      throw error;
    }
  },

  logout: () => {
    delete apiClient.defaults.headers.common["Authorization"];
    set({
      token: null,
      user: null,
      isAuthenticated: false,
    });
  },
}));

export default authStore;
