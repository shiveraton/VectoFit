import axios from "axios";

export const publicClient = axios.create({
  baseURL: "/api/annotator/",
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
});

export async function initializeCsrf() {
  const { data } = await publicClient.get("csrf/");
  publicClient.defaults.headers.common["X-CSRFToken"] = data.csrfToken;
}

export async function publicLogout() {
  await initializeCsrf();
  await publicClient.post("logout/");
}
