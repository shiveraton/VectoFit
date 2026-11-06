# VectoFit admin — React

The complete React/TypeScript port lives here. All 49 Vue components have `.tsx` counterparts; runtime state and rendering use React, React Router, React Query, Zustand and plain CSS Modules. The unchanged `../vectofit_admin` folder remains the reference application. No Vue runtime or SFC loader is required to run this app.

```powershell
cd admin-react
npm install
npm run dev -- --port 5174
```

Run Django on port 8000. The `/api` development proxy and copied environment handling match the reference. For side-by-side comparison, run `npm run dev -- --port 5173` in `vectofit_admin` in another terminal. Use `npm run dev:public` with the respective port for public annotator mode.

Scripts: `dev`, `build`, `preview`, `build:public`, `build:private`, `dev:public`. Default/private output is `dist-private`; public output is `dist-public`. Public mode has a separate entry/router and rejects private admin/auth modules during bundling.

Private admin and annotator workspaces use the same validated token condition and role guard; both private sign-outs clear the token and cached data. Public mode uses the existing cookie/CSRF API. `/evaluation` continues to redirect to `/models`; unregistered source components have not gained routes.

See [migration status](MIGRATION_STATUS.md) and [route parity checklist](PARITY_CHECKLIST.md) for evidence and remaining live-backend/manual checks. Browser verification used intercepted synthetic API responses. Production deployment was not changed. Phase 4 changes are deliberately uncommitted for user review.
