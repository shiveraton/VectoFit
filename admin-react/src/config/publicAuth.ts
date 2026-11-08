import axios from "axios";

export const publicClient = axios.create({
  baseURL: `${(import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "")}/annotator/`,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  timeout: 15000,
});

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

export async function getPublicSession(signal?: AbortSignal) {
  const { data } = await publicClient.get<unknown>('me/', { signal });
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

export function publicAuthError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      return 'The annotation service took too long to respond. Please try again.';
    }
    if (!error.response) return 'Unable to reach the annotation service. Check your connection and try again.';
    const { status, data } = error.response;
    if (status === 404) return 'The sign-in service was not found. Please contact the administrator.';
    if (status >= 500) return 'The annotation service encountered an error. Please try again later.';
    if (status === 403 && typeof data === 'string' && data.includes('CSRF verification failed')) {
      return 'The sign-in security check failed. Reload this page and try again. If it persists, contact the administrator.';
    }
    if ((status === 400 || status === 401 || status === 403) && data && typeof data === 'object') {
      const messages = Object.values(data).flatMap(value =>
        typeof value === 'string' ? [value] : Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [],
      );
      if (messages.length) return messages.join(' ');
    }
    return `The request failed (HTTP ${status}). Please try again.`;
  }
  // Client-side response validation errors carry specific, actionable messages.
  return error instanceof Error ? error.message : 'Sign-in could not be completed. Please try again.';
}
