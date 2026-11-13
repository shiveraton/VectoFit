import { useModels } from './useModels';
import { useDatasets } from './useDatasets';
import { useTraining } from './useTraining';
export function useDashboard() {
  const model = useModels(); const dataset = useDatasets(); const training = useTraining();
  const currentModel = model.models.find(item => item.is_active) ?? model.models[0] ?? null;
  return { currentModel, isLoading: model.isLoading || model.isStateLoading || dataset.isLoading || training.isLoading, error: [model.error, dataset.errorMessage, training.error].filter(Boolean).join(' '),
    dashboardCards: [
      { label: 'Registered Datasets', value: dataset.datasets.length, description: 'Available benchmark datasets', icon: 'D', variant: 'samples' as const },
      { label: 'Registered Models', value: model.models.length, description: 'Total trained model versions', icon: 'M', variant: 'version' as const },
      { label: 'Current Model', value: currentModel ? `v${currentModel.version}` : 'None', description: currentModel?.name ?? 'No registered model', icon: 'M', variant: 'correct' as const },
      { label: 'Active Training Runs', value: training.trainingJobs.filter(job => ['RUNNING','PENDING'].includes(job.status)).length, description: 'Currently executing pipeline jobs', icon: 'T', variant: 'samples' as const },
    ], fetchAllDashboardData: async (force = false) => { dataset.setErrorMessage(''); await Promise.all([model.fetchModels(force), dataset.fetchDatasets(force), training.fetchTrainingData(force)]); } };
}
