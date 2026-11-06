import axios from "axios";
import useAuthStore from "../stores/useAuthStore";

const apiClient = axios.create({
  baseURL: __VECTOFIT_API_URL__,
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
