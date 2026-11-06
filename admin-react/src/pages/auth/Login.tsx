import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router';
import { privateHome, signIn } from '../../auth/privateSession';
export default function Login() {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState(''); const [password, setPassword] = useState('');
  const login = useMutation({ mutationFn: () => signIn(identifier, password), onSuccess: (user) => navigate(privateHome(user.is_annotator), { replace: true }) });
  const loginError = login.isError ? login.error.message === 'Sign-in could not be completed. Please try again.' ? login.error.message : 'Unable to sign in. Check your credentials and connection, then try again.' : '';
  return <section className="login-card"><div className="login-header"><h1>Sign in to VectoFit</h1><p>Access your research and annotation workspace.</p></div><form onSubmit={(event) => { event.preventDefault(); if (!login.isPending) login.mutate(); }} aria-busy={login.isPending}><div className="form-group"><label htmlFor="identifier">Username or Email</label><input id="identifier" value={identifier} onChange={(event) => setIdentifier(event.target.value)} type="text" placeholder="Enter your username or email" autoComplete="username" required /></div><div className="form-group"><label htmlFor="password">Password</label><input id="password" value={password} onChange={(event) => setPassword(event.target.value)} type="password" placeholder="Enter your password" autoComplete="current-password" required /></div>{loginError && <p className="auth-error" role="alert">{loginError}</p>}<button type="submit" className="primary-button auth-submit" disabled={login.isPending}>{login.isPending ? 'Signing in...' : 'Sign in'}</button></form><div className="register-link"><span>Don't have an account?</span><Link to="/register">Sign Up</Link></div></section>;
}
