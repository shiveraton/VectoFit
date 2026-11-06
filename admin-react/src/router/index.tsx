import { createBrowserRouter, Navigate } from 'react-router';
import PrivateGuard from '../auth/PrivateGuard';
import AuthLayout from '../layouts/AuthLayout';
import AdminLayout from '../layouts/AdminLayout';
import AnnotatorLayout from '../layouts/AnnotatorLayout';
import Login from '../pages/auth/Login';
import Register from '../pages/auth/Register';
// Page elements are attached as each source page is ported in Phase 4.
export default createBrowserRouter([
  { element: <PrivateGuard role="admin" />, children: [
    { path: '/', element: <AdminLayout />, children: [
      { path: 'dashboard' }, { path: 'dataset' }, { path: 'dataset/:id/annotate' },
      { path: 'training' }, { path: 'evaluation', element: <Navigate to="/models" replace /> },
      { path: 'models' }, { path: 'pilot-results' },
    ] },
  ] },
  { element: <PrivateGuard role="annotator" />, children: [
    { path: '/annotator', element: <AnnotatorLayout />, children: [{ index: true }, { path: ':id' }] },
  ] },
  { element: <AuthLayout />, children: [{ path: '/login', element: <Login /> }, { path: '/register', element: <Register /> }] },
]);
