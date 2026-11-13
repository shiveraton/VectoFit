import { useModels } from './useModels';
export interface EvaluationModel { id: string; name: string; version: string; type: string; accuracy?: number }
export interface EvaluationMetric { id: string; name: string; category: string; description: string; selected: boolean }
export interface EvaluationRecord { id: string; modelName: string; datasetName: string; score: number; status: 'COMPLETED' | 'RUNNING' | 'FAILED' | 'PENDING'; createdAt: string; duration: string }
export function useEvaluation() {
  const model = useModels(); const evaluation = model.modelState?.evaluation ?? null, training = model.modelState?.training ?? null;
  const formatPercent = (value: number | null | undefined) => value == null ? '—' : `${(value * 100).toFixed(1)}%`;
  const summaryCards = [
    { label: 'ACCURACY', value: formatPercent(evaluation?.accuracy), description: 'Correct predictions on the held-out test set' },
    { label: 'BALANCED ACCURACY', value: formatPercent(evaluation?.balanced_accuracy), description: 'Average recall across classes' },
    { label: 'PRECISION', value: formatPercent(evaluation?.precision), description: 'Precision reported by the training evaluation' },
    { label: 'F1 SCORE', value: formatPercent(evaluation?.f1), description: 'F1 reported by the training evaluation' },
  ];
  return { ...model, evaluation, training, summaryCards, evaluationAvailable: training?.status === 'COMPLETED' && evaluation?.accuracy != null, formatPercent,
    formatDate: (value: string | null | undefined) => !value || Number.isNaN(new Date(value).getTime()) ? '—' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)),
    formatAngle: (value: string | null | undefined) => value ? value.charAt(0).toUpperCase() + value.slice(1) : 'Not specified',
    formatTarget: (value: string | null | undefined) => value === 'knee_alignment' ? 'Frontal-plane knee alignment' : 'Unsupported model setup',
  };
}
