import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Link, Navigate, Outlet, useLocation } from 'react-router';
import { getPublicSession } from '../config/publicAuth';
import { queryKeys } from '../query';
export default function PublicGuard() {
  const location = useLocation();
  const session = useQuery({ queryKey: [...queryKeys.publicSession, location.key], queryFn: ({ signal }) => getPublicSession(signal), gcTime: 0, networkMode: 'always' });
  const login = '/annotator/login?next=' + encodeURIComponent(location.pathname + location.search + location.hash);
  if (session.isPending || session.isFetching) return <main aria-busy="true">Loading session...</main>;
  if (session.isError) {
    const status = axios.isAxiosError(session.error) ? session.error.response?.status : undefined;
    if (status === 401 || status === 403) return <Navigate to={login} replace />;
    return <main className="login-card" style={{ maxWidth: 440, margin: '40px auto' }}>
      <div className="login-header"><h1>Unable to check your session</h1><p role="alert">The annotation service could not be reached or returned an invalid response. Please try again.</p></div>
      <button type="button" className="primary-button" onClick={() => { void session.refetch(); }}>Try again</button>
      <div className="login-link"><Link to={login}>Go to sign in</Link></div>
    </main>;
  }
  return <Outlet />;
}
