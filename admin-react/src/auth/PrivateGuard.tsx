import { useQuery } from '@tanstack/react-query';
import { Navigate, Outlet, useLocation } from 'react-router';
import { useAuthStore } from '../state/auth';
import { queryKeys } from '../query';
import { privateHome, validatePrivateSession } from './privateSession';

export default function PrivateGuard({ role }: { role: 'admin' | 'annotator' }) {
  const token = useAuthStore((state) => state.token);
  const location = useLocation();
  const session = useQuery({
    queryKey: [...queryKeys.session, location.key],
    queryFn: validatePrivateSession,
    enabled: Boolean(token),
    staleTime: 0,
    refetchOnMount: 'always',
  });
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname + location.search + location.hash }} />;
  if (session.isPending || session.isFetching) return <main aria-busy="true">Loading session...</main>;
  if (session.isError || !session.data) {
    return <main><p role="alert">Unable to verify your session. Please try again.</p><button type="button" className="secondary-button" onClick={() => { void session.refetch(); }}>Retry</button></main>;
  }
  const isAnnotator = session.data.is_annotator;
  if ((role === 'annotator') !== isAnnotator) return <Navigate to={privateHome(isAnnotator)} replace />;
  return <Outlet />;
}

