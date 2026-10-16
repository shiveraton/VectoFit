import axios from "axios";
import { Platform } from "react-native";
import useAuthStore from "../stores/useAuthStore";

const PORT = "8000";

const API_URL = Platform.select({
  ios: `http://localhost:${PORT}/api`,
  // 10.0.2.2 for Android Emulator, or "http://192.168.1.101:8000/api" for a physical device
  android: `http://192.168.1.101:${PORT}/api`,
  default: `http://localhost:${PORT}/api`,
});

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;

    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

export default apiClient;
