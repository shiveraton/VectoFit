import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router';
import { initializeCsrf, publicClient, validateIdentity } from '../../config/publicAuth';
import styles from './PublicAuth.module.css';
export default function PublicAuth() {
  const location = useLocation(); const navigate = useNavigate(); const [params] = useSearchParams();
  const registering = location.pathname.endsWith('/register');
  const candidate = params.get('next');
  const next = candidate && /^\/annotator(?:\/\d+)?(?:[?#].*)?$/.test(candidate) ? candidate : '/annotator';
  const [username, setUsername] = useState(''); const [email, setEmail] = useState('');
  const [password, setPassword] = useState(''); const [confirmation, setConfirmation] = useState(''); const [invitation, setInvitation] = useState('');
  const submit = useMutation({ mutationFn: async () => {
    await initializeCsrf();
    if (registering) await publicClient.post('register/', { username, email, password, confirm_password: confirmation, invitation_code: invitation });
    const { data } = await publicClient.post('login/', { username, password });
    validateIdentity(data);
    if (typeof data.csrfToken !== 'string' || !data.csrfToken) throw new Error('Invalid sign-in response.');
    publicClient.defaults.headers.common['X-CSRFToken'] = data.csrfToken;
    setPassword(''); setConfirmation(''); setInvitation('');
    await navigate(next, { replace: true });
  } });
  const response = submit.error as { response?: { data?: unknown } } | null;
  const error = submit.isError ? response?.response?.data ? JSON.stringify(response.response.data) : 'Unable to connect. Please try again.' : '';
  return <main className={styles['public-auth']}><form onSubmit={(event) => { event.preventDefault(); if (!submit.isPending) submit.mutate(); }}><h1>{registering ? 'Create annotator account' : 'Annotator sign in'}</h1><label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" maxLength={150} required /></label>{registering && <label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" required /></label>}<label>Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete={registering ? 'new-password' : 'current-password'} required /></label>{registering && <><label>Confirm password<input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} type="password" autoComplete="new-password" required /></label><label>Invitation code<input value={invitation} onChange={(event) => setInvitation(event.target.value)} type="password" autoComplete="off" required /></label></>}{error && <p role="alert">{error}</p>}<button className="primary-button" disabled={submit.isPending}>{submit.isPending ? 'Please wait...' : registering ? 'Register and sign in' : 'Sign in'}</button><Link to={(registering ? '/annotator/login' : '/annotator/register') + '?next=' + encodeURIComponent(next)}>{registering ? 'Already registered? Sign in' : 'Register with an invitation'}</Link></form></main>;
}
