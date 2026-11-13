import axios from 'axios';
export function messageFromError(error: unknown, fallback: string): string {
  const data: unknown = axios.isAxiosError(error) ? error.response?.data : undefined;
  if (data && typeof data === 'object') {
    for (const key of ['detail', 'error_message', 'message']) {
      const value = (data as Record<string, unknown>)[key];
      if (typeof value === 'string' && value) return value;
    }
  }
  return error instanceof Error ? error.message : fallback;
}
export function responseMessage(error: unknown, fallback: string): string {
  const data: unknown = axios.isAxiosError(error) ? error.response?.data : undefined;
  return data ? JSON.stringify(data) : fallback;
}

export function trainingErrorMessage(error: unknown, fallback: string): string {
  const data: unknown = axios.isAxiosError(error) ? error.response?.data : undefined;
  if (data && typeof data === 'object') {
    const record = data as Record<string, unknown>;
    for (const key of ['detail','error_message','message']) if (typeof record[key] === 'string' && record[key]) return record[key];
    const messages: string[] = [];
    const collect = (value: unknown, prefix: string) => {
      if (typeof value === 'string') messages.push(prefix ? prefix + ': ' + value : value);
      else if (Array.isArray(value)) value.forEach(item => collect(item, prefix));
      else if (value && typeof value === 'object') Object.entries(value).forEach(([key, item]) => collect(item, prefix ? prefix + '.' + key : key));
    };
    collect(record, ''); if (messages.length) return messages.join(' · ');
  }
  return typeof error === 'string' ? error : messageFromError(error, fallback);
}
