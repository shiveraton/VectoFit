import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router';
import { initializeCsrf, publicAuthError, publicClient, validateIdentity } from '../../config/publicAuth';
import logo from '../../assets/images/vectofit-tm2.png';
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
  const error = submit.isError ? publicAuthError(submit.error) : '';
  return <div className={styles['public-auth']}><header className={styles.brand}><img src={logo} alt="VectoFit" /></header><main className={styles.content}><section className={registering ? 'register-card' : 'login-card'}><div className={registering ? 'register-header' : 'login-header'}><h1>{registering ? 'Create annotator account' : 'Sign in to VectoFit'}</h1><p>{registering ? 'Join the VectoFit annotation workspace.' : 'Access your VectoFit annotation workspace.'}</p></div><form aria-busy={submit.isPending} onSubmit={(event) => { event.preventDefault(); if (!submit.isPending) submit.mutate(); }}><label className="form-group">Username<input placeholder="Enter your username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" maxLength={150} required /></label>{registering && <label className="form-group">Email<input placeholder="Enter your email" value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" required /></label>}<label className="form-group">Password<input placeholder={registering ? 'Create a password' : 'Enter your password'} value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete={registering ? 'new-password' : 'current-password'} required /></label>{registering && <><label className="form-group">Confirm password<input placeholder="Re-enter password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} type="password" autoComplete="new-password" required /></label><label className="form-group">Invitation code<input placeholder="Enter your invitation code" value={invitation} onChange={(event) => setInvitation(event.target.value)} type="password" autoComplete="off" required /></label></>}{error && <p className="auth-error" role="alert">{error}</p>}<button type="submit" className="primary-button auth-submit" disabled={submit.isPending}>{submit.isPending ? 'Please wait...' : registering ? 'Register and sign in' : 'Sign in'}</button></form><div className={registering ? 'login-link' : 'register-link'}><Link to={(registering ? '/annotator/login' : '/annotator/register') + '?next=' + encodeURIComponent(next)}>{registering ? 'Already registered? Sign in' : 'Register with an invitation'}</Link></div></section></main><footer className={styles.footer}><p>{"\u00a9 2026 VectoFit"}</p></footer></div>;
}
