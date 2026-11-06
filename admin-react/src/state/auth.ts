import { create } from 'zustand';

function readToken(): string | null {
  const value = localStorage.getItem('token')?.trim();
  return value && value !== 'undefined' && value !== 'null' ? value : null;
}

interface AuthState {
  token: string | null;
  setToken: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: readToken(),
  setToken: (value) => {
    const token = value.trim();
    if (!token || token === 'null' || token === 'undefined') throw new Error('Missing authentication token.');
    localStorage.setItem('token', token);
    set({ token });
  },
  logout: () => {
    localStorage.removeItem('token');
    set({ token: null });
  },
}));

// Cross-tab sign-in and sign-out must update route guards as well as requests.
window.addEventListener('storage', (event) => {
  if (event.storageArea === localStorage && (event.key === 'token' || event.key === null)) {
    useAuthStore.setState({ token: readToken() });
  }
});

export const getAuthToken = () => useAuthStore.getState().token;
