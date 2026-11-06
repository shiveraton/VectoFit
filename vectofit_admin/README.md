# VectoFit Admin Console

Vue 3, TypeScript, and Vite interface for dataset annotation, model training, and participant/session administration.

## Local development

1. Copy `.env.example` to `.env` and set `VITE_API_URL` to the backend API root, including `/api`.
2. Run `npm ci` and `npm run dev`.

The backend must be running and configured to allow the console’s local origin. `npm run build` performs the Vue TypeScript check and production build.
