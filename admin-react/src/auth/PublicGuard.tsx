import { useQuery } from '@tanstack/react-query';
import { Navigate, Outlet, useLocation } from 'react-router';
import { getPublicSession } from '../config/publicAuth';
import { queryKeys } from '../query';
export default function PublicGuard() {
  const location = useLocation();
  // Include the destination to preserve the source's per-navigation session check.
  const session = useQuery({ queryKey: [...queryKeys.publicSession, location.key], queryFn: getPublicSession, gcTime: 0 });
  if (session.isPending || session.isFetching) return <main aria-busy="true">Loading session...</main>;
  if (session.isError) return <Navigate to={'/annotator/login?next=' + encodeURIComponent(location.pathname + location.search + location.hash)} replace />;
  return <Outlet />;
}
