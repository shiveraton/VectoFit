import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router/dom';
import router from './router/index';
import { queryClient } from './query';
import './assets/styles/index.css';
createRoot(document.getElementById('app')!).render(<QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>);
