import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router';
import { signOut } from '../auth/privateSession';
import logo from '../assets/images/vectofit-tm2.png';
import styles from './AdminLayout.module.css';
const navigation = [
    { to: '/dashboard', label: 'Overview', path: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z' },
    { to: '/dataset', label: 'Datasets', path: 'M3 7v12a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7 M3 7V5a2 2 0 0 1 2-2h5l2 4h9 M3 7h18 M8 12h8 M8 16h5' },
    { to: '/training', label: 'Training', path: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2' },
    { to: '/models', label: 'Model Registry', path: 'm12 3 9 5-9 5-9-5 9-5z M3 12l9 5 9-5 M3 16l9 5 9-5' },
    { to: '/pilot-results', label: 'Pilot Results', path: 'M9 3h6 M10 3v7L4 20a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1l-6-10V3 M8 15h8' },
];
const cx = (...names: string[]) => names.flatMap((name) => styles[name] ? [name, styles[name]] : [name]).join(' ');
export default function AdminLayout() {
    const [menuOpen, setMenuOpen] = useState(false);
    const location = useLocation();
    const navigate = useNavigate();
    useEffect(() => setMenuOpen(false), [location.key]);
    const annotation = /^\/dataset\/[^/]+\/annotate$/.test(location.pathname);
    const pageLabel = annotation ? 'Dataset annotation' : navigation.find((item) => location.pathname.startsWith(item.to))?.label ?? 'Workspace';
    return <div className={cx('admin-layout')}>
    <a className={cx('skip-link')} href="#admin-content">Skip to content</a>
    <aside className={cx('sidebar')}><div className={cx('sidebar-brand')}><NavLink to="/dashboard" aria-label="VectoFit overview" className={cx('brand-link')}><img src={logo} alt="VectoFit"/></NavLink><button className={cx('menu-toggle')} type="button" aria-controls="admin-navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? 'Close menu' : 'Menu'}</button></div>
    <nav id="admin-navigation" className={cx('sidebar-nav', ...(menuOpen ? ['is-open'] : []))} aria-label="Admin navigation" onKeyDown={(event) => { if (event.key === 'Escape')
        setMenuOpen(false); }}>
      <div className={cx('nav-section')}><span className={cx('nav-title')}>Workspace</span>{navigation.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => cx('nav-link', ...(isActive || (item.to === '/dataset' && annotation) ? ['is-current'] : []))}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={item.path}/></svg>{item.label}</NavLink>)}</div>
      <div className={cx('nav-section', 'system-section')}><span className={cx('nav-title')}>Administration</span>{['Users', 'Activity Logs', 'Settings'].map((label) => <div key={label} className={cx('nav-unavailable')}><span>{label}</span><small>Unavailable</small></div>)}</div>
      <div className={cx('sidebar-footer')}><span className={cx('workspace-caption')}>VectoFit Admin Portal</span><button type="button" className={cx('sign-out')} onClick={() => { signOut(); void navigate('/login', { replace: true }); }}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M9 5H4v14h5 M14 8l4 4-4 4 M8 12h10"/></svg>Sign out</button></div>
    </nav></aside>
    <div className={cx('admin-main')}><header className={cx('admin-header')}><div className={cx('workspace-breadcrumb')}><span>Workspace</span><span aria-hidden="true">/</span><strong>{pageLabel}</strong></div><span className={cx('admin-role')}>Administrator</span></header><main id="admin-content" className={cx('admin-content')} tabIndex={-1}><Outlet /></main></div>
  </div>;
}
