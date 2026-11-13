import { QueryClient } from "@tanstack/react-query";
export const queryKeys = {
  session: ["auth", "session"] as const,
  publicSession: ["auth", "public-session"] as const,
  datasets: ["datasets"] as const,
  participants: ["participants"] as const,
  annotation: (id: number) => ["annotation", id] as const,
  annotationDatasets: ["annotation-datasets"] as const,
  annotationPool: ["annotation-pool"] as const,
  models: ["models"] as const,
  model: (id: number) => ["models", id] as const,
  training: ["training"] as const,
  pilot: ["pilot"] as const,
};
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
    },
    mutations: { retry: false },
  },
});
