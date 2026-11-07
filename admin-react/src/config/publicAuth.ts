import axios from "axios";

export const publicClient = axios.create({
  baseURL: `${(import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "")}/annotator/`,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
});

// A successful SPA fallback response is HTML, not a successful API request.
publicClient.interceptors.response.use((response) => {
  if (!String(response.headers['content-type'] || '').includes('application/json')) {
    throw new Error('The annotation API returned an invalid response. Check the production API routing.');
  }
  return response;
});

export function validateIdentity(data: unknown) {
  if (!data || typeof data !== 'object' || !('id' in data) ||
      !Number.isInteger(data.id) || Number(data.id) <= 0 ||
      !('username' in data) || typeof data.username !== 'string' ||
      !('is_annotator' in data) || data.is_annotator !== true) {
    throw new Error('Invalid annotator session.');
  }
  return data;
}

export async function getPublicSession() {
  const { data } = await publicClient.get<unknown>('me/');
  return validateIdentity(data);
}

export async function initializeCsrf() {
  const { data } = await publicClient.get("csrf/");
  if (typeof data?.csrfToken !== 'string' || !data.csrfToken) {
    throw new Error('Invalid CSRF response.');
  }
  publicClient.defaults.headers.common["X-CSRFToken"] = data.csrfToken;
}

export async function publicLogout() {
  await initializeCsrf();
  await publicClient.post("logout/");
}
