# VectoFit admin — React

The complete React/TypeScript port lives here. All 49 Vue components have `.tsx` counterparts; runtime state and rendering use React, React Router, React Query, Zustand and plain CSS Modules. The unchanged `../vectofit_admin` folder remains the reference application. No Vue runtime or SFC loader is required to run this app.

```powershell
cd admin-react
npm install
npm run dev -- --port 5174
```

Run Django on port 8000. The `/api` development proxy and copied environment handling match the reference. For side-by-side comparison, run `npm run dev -- --port 5173` in `vectofit_admin` in another terminal. Use `npm run dev:public` with the respective port for public annotator mode.

Scripts: `dev`, `build`, `preview`, `build:public`, `build:private`, `dev:public`. Default/private output is `dist-private`; public output is `dist-public`. Public mode has a separate entry/router and rejects private admin/auth modules during bundling.

## Vercel public annotator

Use `admin-react` as the Vercel project root. Its `vercel.json` builds the public bundle and proxies `/api/annotator/*` to `https://vectofit.onrender.com/api/annotator/*` before applying the annotator page fallback. Keep `VITE_API_BASE_URL` unset in Vercel so all requests, including session cookies and video URLs, stay on the frontend origin. `VITE_API_URL` does not control public builds.

On Render, add `https://vecto-eopvoc8oa-st4lwart.vercel.app` to `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS`, preserving other required origins. Ensure `ALLOWED_HOSTS` includes `vectofit.onrender.com`. Use the stable Vercel production origin instead if that deployment URL changes; Django settings must match the origin visitors actually use. Keep session/CSRF cookies host-only (no cookie domain override). Restart Render after environment changes and redeploy Vercel after committing the routing changes.

Verify through the Vercel domain: `/api/annotator/csrf/` must return JSON and set a CSRF cookie; anonymous `/api/annotator/me/` and `/api/annotator/datasets/` must return 403. Then verify registration, sign-in, refresh, and sign-out in a browser. HTML from any API URL indicates incorrect routing or an older deployment.

Protected playback streams through Django on Render; Nginx `X-Accel-Redirect` is no longer required. The public video endpoint checks the logged-in annotator and active assignment on each request, supports single byte ranges for seeking, and sends private/no-store responses. Keep the same-origin `/api/annotator/*` proxy. Render must have persistent media storage mounted at `MEDIA_ROOT`, containing the files referenced by the dataset records. Local uploads do not automatically exist on Render. Session FPS extraction still requires local file paths.

Private admin and annotator workspaces use the same validated token condition and role guard; both private sign-outs clear the token and cached data. Public mode uses the existing cookie/CSRF API. `/evaluation` continues to redirect to `/models`; unregistered source components have not gained routes.

See [migration status](MIGRATION_STATUS.md) and [route parity checklist](PARITY_CHECKLIST.md) for evidence and remaining live-backend/manual checks. Browser verification used intercepted synthetic API responses. Production deployment was not changed. Phase 4 changes are deliberately uncommitted for user review.
