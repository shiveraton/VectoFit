import { createBrowserRouter, Navigate } from 'react-router';
import PrivateGuard from '../auth/PrivateGuard';
import AuthLayout from '../layouts/AuthLayout';
import AdminLayout from '../layouts/AdminLayout';
import AnnotatorLayout from '../layouts/AnnotatorLayout';
import Login from '../pages/auth/Login';
import Register from '../pages/auth/Register';
import Dashboard from '../pages/dashboard/Dashboard';
import Datasets from '../pages/views/Datasets';
import DatasetAnnotation from '../pages/views/DatasetAnnotation';
import Training from '../pages/views/Training';
import Models from '../pages/views/Models';
import PilotResults from '../pages/views/PilotResults';
import AnnotatorHome from '../pages/views/AnnotatorHome';
export default createBrowserRouter([
  { element: <PrivateGuard role="admin" />, children: [
    { path: '/', element: <AdminLayout />, children: [
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'dataset', element: <Datasets /> },
      { path: 'dataset/:id/annotate', element: <DatasetAnnotation /> },
      { path: 'training', element: <Training /> },
      { path: 'evaluation', element: <Navigate to="/models" replace /> },
      { path: 'models', element: <Models /> },
      { path: 'pilot-results', element: <PilotResults /> },
    ] },
  ] },
  { element: <PrivateGuard role="annotator" />, children: [
    { path: '/annotator', element: <AnnotatorLayout />, children: [{ index: true, element: <AnnotatorHome /> }, { path: ':id', element: <DatasetAnnotation /> }] },
  ] },
  { element: <AuthLayout />, children: [{ path: '/login', element: <Login /> }, { path: '/register', element: <Register /> }] },
  // Vue renders an empty RouterView for unmatched private URLs.
  { path: '*', element: null },
]);
