import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { participantService } from '../services/participantService';
import { queryKeys } from '../query';
import { messageFromError } from './errors';
export function useParticipants() {
  const cache = useQueryClient();
  const [successMessage, setSuccessMessage] = useState('');
  const query = useQuery({ queryKey: queryKeys.participants, queryFn: participantService.getParticipants });
  const create = useMutation({ mutationFn: participantService.createParticipant, onSuccess: async participant => {
    setSuccessMessage(`Participant ${participant.participant_code} created.`);
    await cache.invalidateQueries({ queryKey: queryKeys.participants });
  } });
  async function createParticipant() { setSuccessMessage(''); try { return await create.mutateAsync(); } catch { return null; } }
  return { participants: query.data ?? [], isLoading: query.isPending, isCreating: create.isPending,
    errorMessage: create.error ? messageFromError(create.error, 'Failed to create participant.') : query.error ? 'Unable to load participants.' : '', successMessage,
    fetchParticipants: () => query.refetch(), createParticipant };
}
