import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { modelService } from '../services/modelService';
import { queryClient, queryKeys } from '../query';
import { messageFromError } from './errors';
export const invalidateModels = () => queryClient.invalidateQueries({ queryKey: queryKeys.models });
export function useModels() {
  const cache = useQueryClient();
  const [selection, setSelection] = useState<number | null>(null);
  const [activationMessage, setActivationMessage] = useState<string | null>(null);
  const registry = useQuery({ queryKey: queryKeys.models, queryFn: modelService.getModels });
  const models = (registry.data ?? []).filter(model => model.prediction_target === 'knee_alignment' && model.feature_schema_version === 'fppa_v2');
  const selectedModelId = selection ?? models.find(model => model.is_active)?.id ?? models[0]?.id ?? null;
  const state = useQuery({ queryKey: queryKeys.model(selectedModelId ?? 0), queryFn: () => modelService.getModelState(selectedModelId!), enabled: selectedModelId !== null });
  const activate = useMutation({ mutationFn: modelService.activateModel, onSuccess: async model => {
    setSelection(model.id); await cache.invalidateQueries({ queryKey: queryKeys.models });
    setActivationMessage('Model activated for its camera angle and prediction target.');
  } });
  const modelState = state.data ?? null;
  const metrics = modelState?.evaluation;
  const summaryCards = [
    { label: 'CURRENT VERSION', value: modelState ? `v${modelState.version}` : '—', description: modelState?.name ?? 'No model registered' },
    { label: 'ACCURACY', value: metrics?.accuracy != null ? `${(metrics.accuracy * 100).toFixed(1)}%` : '—', description: metrics ? 'Held out test set' : 'No evaluation available' },
    { label: 'F1 SCORE', value: metrics?.f1 != null ? `${(metrics.f1 * 100).toFixed(1)}%` : '—', description: metrics ? 'Macro-averaged F1 across good and bad FPPA labels' : 'No evaluation available' },
    { label: 'FEATURES', value: modelState?.features.selected.length ?? '—', description: 'Model input features' },
  ];
  return { models, modelState, selectedModelId, selectedModel: models.find(model => model.id === selectedModelId) ?? null, summaryCards,
    isLoading: registry.isPending, isStateLoading: selectedModelId !== null && state.isFetching, isActivatingModel: activate.isPending, activationMessage,
    error: activate.error ? messageFromError(activate.error, 'Failed to activate model.') : state.error ? messageFromError(state.error, 'Failed to load model state.') : registry.error ? messageFromError(registry.error, 'Failed to load model registry.') : null,
    fetchModels: async (_force = false) => { setSelection(null); return registry.refetch(); }, fetchModelState: (id: number) => { setSelection(id); return state.refetch(); },
    selectModel: (id: number) => { if (id === selectedModelId && !state.data) void state.refetch(); setSelection(id); },
    activateModel: async (id: number) => { setActivationMessage(null); try { await activate.mutateAsync(id); } catch { /* error displayed above */ } },
  };
}
