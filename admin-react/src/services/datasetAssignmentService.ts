import client from '../config/client';
export interface Annotator { id: number; username: string }
export interface Assignment { id: number; annotator: Annotator; is_active: boolean; assigned_at: string; reviewed_count: number; sample_count: number; account_eligible: boolean }
export interface AssignmentEvent { id: number; annotator: Annotator; actor: Annotator | null; action: 'granted' | 'revoked'; created_at: string }
export interface Page<T> { count: number; next: string | null; previous: string | null; results: T[] }
export const datasetAssignmentService = {
  async list(id: number, page: number) { return (await client.get<Page<Assignment> & { eligible_sample_count: number }>(`/datasets/${id}/assignments/`, { params: { page }, timeout: 15000 })).data; },
  async annotators(search: string, page: number) { return (await client.get<Page<Annotator>>('/datasets/annotators/', { params: { search, page }, timeout: 15000 })).data; },
  async set(id: number, annotator: number, is_active: boolean) { await client.put(`/datasets/${id}/assignments/${annotator}/`, { is_active }, { timeout: 15000 }); },
  async events(id: number, page: number) { return (await client.get<Page<AssignmentEvent>>(`/datasets/${id}/assignments/events/`, { params: { page }, timeout: 15000 })).data; },
};
