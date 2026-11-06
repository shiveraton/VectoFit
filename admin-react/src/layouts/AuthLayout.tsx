import { bindStyles } from '../presentation';
import { Outlet } from 'react-router';
import logo from '../assets/images/vectofit-tm2.png';
import styles from './AuthLayout.module.css';
const cx = bindStyles(styles);
export default function AuthLayout() {
    return <div className={cx('auth-layout')}><header className={cx('auth-header')}><img src={logo} alt="VectoFit"/></header><main className={cx('auth-content')}><Outlet /></main><footer className={cx('auth-footer')}><p>© 2026 VectoFit</p></footer></div>;
}
