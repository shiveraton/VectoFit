import { createBrowserRouter, Navigate, useParams } from 'react-router';
import PublicGuard from '../auth/PublicGuard';
import AnnotatorLayout from '../layouts/AnnotatorLayout';
import PublicAuth from '../pages/auth/PublicAuth';
import AnnotatorHome from '../pages/views/AnnotatorHome';
import DatasetAnnotation from '../pages/views/DatasetAnnotation';
function NotFound() { return <main><h1>404</h1><p>Page not found.</p></main>; }
function NumericDataset() {
  const { id } = useParams();
  // Validate before mounting the session guard, as Vue's route regex does.
  return id && /^\d+$/.test(id) ? <PublicGuard /> : <NotFound />;
}
export default createBrowserRouter([
  { path: '/', element: <Navigate to="/annotator" replace /> },
  { path: '/annotator/login', element: <PublicAuth /> },
  { path: '/annotator/register', element: <PublicAuth /> },
  { path: '/annotator', element: <PublicGuard />, children: [{ element: <AnnotatorLayout />, children: [{ index: true, element: <AnnotatorHome /> }] }] },
  { path: '/annotator/:id', element: <NumericDataset />, children: [{ element: <AnnotatorLayout />, children: [{ index: true, element: <DatasetAnnotation /> }] }] },
  { path: '*', element: <NotFound /> },
]);
