import { Outlet } from 'react-router';
import logo from '../assets/images/vectofit-tm2.png';
import styles from './AuthLayout.module.css';
export default function AuthLayout() {
  return <div className={styles['auth-layout']}><header className={styles['auth-header']}><img src={logo} alt="VectoFit" /></header><main className={styles['auth-content']}><Outlet /></main><footer className={styles['auth-footer']}><p>© 2026 VectoFit</p></footer></div>;
}
