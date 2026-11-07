import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { datasetService, type CreateDatasetPayload } from '../services/datasetService';
import { queryKeys } from '../query';
import { responseMessage } from './errors';
const emptyForm = (): CreateDatasetPayload => ({ name: '', description: '', participant: 0, exercise_type: 'bodyweight_squat', purpose: 'training', primary_target: 'squat_quality', secondary_target: 'biomechanical_errors', view_angle: null, video_file: null });
export function useDatasets() {
  const cache = useQueryClient();
  const [datasetForm, setDatasetForm] = useState(emptyForm);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const query = useQuery({ queryKey: queryKeys.datasets, queryFn: datasetService.getDatasets, refetchInterval: query => query.state.data?.some(dataset => dataset.status === 'PROCESSING') ? 3000 : false });
  const create = useMutation({ mutationFn: datasetService.createDatasetWithVideo, onSuccess: async () => {
    setSuccessMessage('Dataset created successfully.'); setDatasetForm(emptyForm()); setIsModalOpen(false);
    await cache.invalidateQueries({ queryKey: queryKeys.datasets });
  } });
  const retry = useMutation({ mutationFn: datasetService.retryDataset, onSuccess: async () => { setSuccessMessage('Dataset processing restarted.'); await cache.invalidateQueries({ queryKey: queryKeys.datasets }); } });
  async function handleCreateDataset() {
    if (create.isPending) return false;
    if (!datasetForm.name.trim()) { setErrorMessage('Dataset name is required.'); return false; }
    if (!datasetForm.video_file) { setErrorMessage('Please select a video.'); return false; }
    if (!datasetForm.participant) { setErrorMessage('Please assign a participant.'); return false; }
    setErrorMessage(''); setSuccessMessage('');
    const payload = new FormData();
    payload.append('name', datasetForm.name.trim());
    for (const key of ['description','exercise_type','purpose','primary_target','secondary_target'] as const) if (datasetForm[key]) payload.append(key, datasetForm[key]);
    payload.append('participant', String(datasetForm.participant));
    if (datasetForm.view_angle !== null) payload.append('view_angle', String(datasetForm.view_angle));
    payload.append('video_file', datasetForm.video_file);
    try { await create.mutateAsync(payload); return true; } catch (error) { setErrorMessage(responseMessage(error, 'Failed to create dataset.')); return false; }
  }
  const datasets = query.data ?? [];
  return { datasets, isLoading: query.isPending, isInitialized: query.isSuccess, isCreating: create.isPending, isModalOpen, datasetForm, setDatasetForm,
    errorMessage: errorMessage || (query.error ? 'Unable to load datasets.' : ''), setErrorMessage, successMessage, setSuccessMessage,
    totalDatasets: datasets.length, totalSamples: datasets.reduce((total, dataset) => total + (dataset.sample_count || 0), 0), totalCorrect: 0, totalIncorrect: 0,
    usableDatasets: datasets.filter(dataset => dataset.is_usable_for_training),
    fetchDatasets: (_force = false) => query.refetch(), refreshDatasets: () => query.refetch(),
    openCreateModal: () => { setDatasetForm(emptyForm()); setErrorMessage(''); setSuccessMessage(''); setIsModalOpen(true); },
    closeCreateModal: () => { if (!create.isPending) setIsModalOpen(false); }, handleCreateDataset,
    retryDataset: async (id: number) => { setErrorMessage(''); setSuccessMessage(''); try { await retry.mutateAsync(id); return true; } catch (error) { setErrorMessage(responseMessage(error, 'Failed to retry dataset.')); return false; } },
  };
}
