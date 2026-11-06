# React migration status

## Approved authentication behavior

The 2026-11-06 follow-up authorizes auth guards and a consistent token condition for both private workspaces. This supersedes the audit's proposed preservation of unguarded private routing and admin logout behavior.

- One Zustand token state persists under localStorage key `token`. Both private layouts clear it on sign-out. Storage events synchronize other tabs.
- The Axios interceptor reads a plain module accessor, never a React hook. Empty tokens and literal `null`/`undefined` values do not authenticate.
- Every private navigation requires the token and validates `/accounts/me/` before rendering an Outlet. Both role trees use the same guard component.
- `is_annotator: true` can enter the annotator tree; `false` can enter the admin tree. A wrong-role destination redirects to the appropriate home. Malformed role responses fail closed.
- Session validation returning 401/403 removes the token. A network/server failure blocks the Outlet and offers Retry without deleting a potentially valid token.
- Token changes cancel and clear the query cache. Validation results for a superseded token cannot authenticate a new identity.
- Login accepts the existing `access_token || token` response and verifies the role before navigating. No refresh endpoint or fixed credential is invented.
- Public mode retains cookie sessions, CSRF initialization, its session check and numeric dataset-route restriction. Private guard modules are excluded from its route graph.

## Completed work

Phase 0 audit; Phase 1 strict TypeScript/Vite React scaffold; Phase 2 copied services, contracts, constants, assets and Axios clients; Phase 3 routing/auth shell, layouts and three authentication pages. Vue and Django source files have no changes.

## Remaining work

**The full migration is not complete.** Phase 4 data-page ports and the Phase 5 route parity checklist remain. The registered data routes currently render their layout only; no data-page component has been attached yet. This branch is an implementation scaffold, not a replacement for the working Vue app. Do not deploy it as a finished admin application.

## Actual verification

- Empty-shell `npm run build`: passed before Phase 1 commit.
- Auth-shell `npm run build`: passed.
- `npx tsc -b`, `npm run build:private`, `npm run build:public`: passed after auth changes.
- Public bundle generation passed its module-exclusion check. Built JS inspection confirmed absence of private guard text, private login text and admin portal content from public output, and presence of private guard text in private output.
- No Vue/Pinia/vue-router imports in React source.
- Ephemeral verification (TypeScript transpilation, actual Zustand state, mocked HTTP/query/router boundaries): passed token persistence, normalization, both roles, missing tokens, 401/403 rejection, network failure retention, malformed role response, login response shapes, identity races, cache cancellation/clearing, cross-tab logout and guard render decisions.
- No manual browser, visual parity, or live backend verification was performed. No test suite was added.

## Local commands

Run Django on port 8000. Use separate terminals from the repository root:

```powershell
cd vectofit_admin
npm run dev -- --port 5173
```

```powershell
cd admin-react
npm install
npm run dev -- --port 5174
```

For public-mode comparison, use `npm run dev:public` in each directory with the same respective port arguments. The React app currently supports comparison of authentication/layout behavior only; data pages remain pending.
