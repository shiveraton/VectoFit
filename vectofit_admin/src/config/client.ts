import axios from "axios";

const client = axios.create({
  baseURL: ["public", "private"].includes(import.meta.env.MODE) ? "/api" : import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
});

client.defaults.baseURL =
  import.meta.env.VITE_API_BASE_URL || client.defaults.baseURL;

client.interceptors.request.use((config) => {
  if (import.meta.env.MODE === "public") return config;
  const token = localStorage.getItem("token");

  if (token) {
    if (typeof config.headers.set === "function") {
      config.headers.set("Authorization", `Token ${token}`);
    } else {
      config.headers.Authorization = `Token ${token}`;
    }
  }

  return config;
});

export default client;
