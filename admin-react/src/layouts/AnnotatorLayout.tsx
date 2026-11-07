import { bindStyles } from '../presentation';
import { Outlet, useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { publicLogout } from '../config/publicAuth';
import { useAuthStore } from '../state/auth';
import logo from '../assets/images/vectofit-tm2.png';
import styles from './AnnotatorLayout.module.css';
const cx = bindStyles(styles);
export default function AnnotatorLayout() {
    const navigate = useNavigate();
    const cache = useQueryClient();
    async function signOut() {
        if (import.meta.env.MODE === 'public') {
            try {
                await publicLogout();
            }
            catch {
                window.alert('The server could not confirm sign out. Your session may still be active.');
            }
            finally {
                await cache.cancelQueries();
                cache.clear();
                await navigate('/annotator/login', { replace: true });
            }
            return;
        }
        useAuthStore.getState().logout();
        await cache.cancelQueries();
        cache.clear();
        await navigate('/login', { replace: true });
    }
    return <div className={cx('annotator-layout')}><header className={cx('annotator-header')}><div className={cx('header-brand')}><img src={logo} alt="VectoFit" className={cx('brand-logo')}/><span className={cx('brand-divider')}/><span className={cx('brand-label')}>Annotation</span></div><button type="button" className="secondary-button" onClick={() => { void signOut(); }}>Sign Out</button></header><main className={cx('annotator-main')}><Outlet /></main></div>;
}
