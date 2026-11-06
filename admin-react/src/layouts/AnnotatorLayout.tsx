import { Outlet, useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { publicLogout } from '../config/publicAuth';
import { useAuthStore } from '../state/auth';
import logo from '../assets/images/vectofit-tm2.png';
import styles from './AnnotatorLayout.module.css';
export default function AnnotatorLayout() {
  const navigate = useNavigate();
  const cache = useQueryClient();
  async function signOut() {
    if (import.meta.env.MODE === 'public') {
      try { await publicLogout(); await cache.cancelQueries(); cache.clear(); await navigate('/annotator/login', { replace: true }); }
      catch { window.alert('Sign out failed. Please try again.'); }
      return;
    }
    useAuthStore.getState().logout();
    await cache.cancelQueries(); cache.clear();
    await navigate('/login', { replace: true });
  }
  return <div className={styles['annotator-layout']}><header className={styles['annotator-header']}><div className={styles['header-brand']}><img src={logo} alt="VectoFit" className={styles['brand-logo']} /><span className={styles['brand-divider']} /><span className={styles['brand-label']}>Annotation</span></div><button type="button" className="secondary-button" onClick={() => { void signOut(); }}>Sign Out</button></header><main className={styles['annotator-main']}><Outlet /></main></div>;
}
