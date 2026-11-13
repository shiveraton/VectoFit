import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router';
import { accountService } from '../../services/accountService';
export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', email: '', password: '', confirmPassword: '', isAnnotator: true });
  const register = useMutation({ mutationFn: () => accountService.register({ username: form.username, email: form.email, password: form.password, confirm_password: form.confirmPassword, is_annotator: form.isAnnotator }), onSuccess: () => navigate('/login') });
  return <section className="register-card"><div className="register-header"><h1>Create an account</h1><p>Join the VectoFit research workspace.</p></div><form onSubmit={(event) => { event.preventDefault(); if (!register.isPending) register.mutate(); }}>
    <div className="form-group"><label htmlFor="username">Username</label><input id="username" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} type="text" placeholder="Enter your username" autoComplete="username" required /></div>
    <div className="form-group"><label htmlFor="email">Email</label><input id="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} type="email" placeholder="Enter your email" autoComplete="email" required /></div>
    <div className="form-group"><label htmlFor="password">Password</label><input id="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} type="password" placeholder="Create a password" autoComplete="new-password" required /></div>
    <div className="form-group"><label htmlFor="confirmPassword">Confirm Password</label><input id="confirmPassword" value={form.confirmPassword} onChange={(event) => setForm({ ...form, confirmPassword: event.target.value })} type="password" placeholder="Re-enter password" autoComplete="new-password" required /></div>
    <label className="annotator-option"><input checked={form.isAnnotator} onChange={(event) => setForm({ ...form, isAnnotator: event.target.checked })} type="checkbox" />Sign up as an annotator</label>
    {register.isError && <p className="error" role="alert">Registration failed. Check the form and try again.</p>}<button type="submit" className="primary-button auth-submit" disabled={register.isPending}>{register.isPending ? 'Creating account...' : 'Create account'}</button></form><div className="login-link"><span>Already have an account?</span><Link to="/login">Sign In</Link></div></section>;
}
