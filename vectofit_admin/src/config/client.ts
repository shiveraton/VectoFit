import axios from "axios";

const client = axios.create({
  baseURL: "http://100.100.28.107:8000/api",
});

client.interceptors.request.use((config) => {
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
