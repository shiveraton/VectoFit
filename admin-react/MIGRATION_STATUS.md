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

## Phase 2 revalidation — 2026-11-06

Rechecked the existing Phase 2 implementation on request; no source-layer omissions or unintended rewrites were found.

- SHA-256 comparison: 19 files are byte-identical to the Vue reference: eight service modules (including their types, interfaces and local constants), seven files under src/assets (including the shared stylesheets), two public assets, config/publicAuth.ts and training/configuration/trainingParameters.ts.
- config/client.ts matches the reference after normalizing line endings and applying only the required getAuthToken import/accessor substitution. Its MODE branches, base URL precedence, endpoints, authorization format and header fallback remain intact. The accessor reads Zustand getState(), not a React hook.
- Local Axios adapter verification passed for development, production, public and private modes: default base URLs, both VITE URL overrides, token changes between requests, missing-token behavior, public-mode token suppression, AxiosHeaders and plain-object header handling. No HTTP requests were sent.
- npm run build passed (strict TypeScript project build followed by Vite).
- No Vue, Pinia or vue-router imports were found in the copied services/configuration. Vue-specific hooks, focus composables and routing remain outside the framework-neutral copy phase. Formatters embedded in those Vue modules require porting with their consumers; they are not standalone source modules that can be copied as-is.
- Vue and Django source files remain unchanged. No new dependencies or permanent test suite were added during this revalidation.

Phase 2 is complete. Data-page ports and full route parity verification remain pending as documented above.

## Phase 3 completion check — 2026-11-06

Reviewed the existing app shell against the reference routers, layouts and the approved token-auth changes. Completed three corrections:

- PublicGuard now waits during every session refetch, including when React Query retains a previous success. Protected content is not rendered before the current navigation's session check finishes.
- Unmatched private URLs use an empty fallback, preserving Vue's blank RouterView output instead of React Router's default error screen. This adds no named page or visible 404 UI; public mode retains its explicit 404 page and numeric dataset-id check.
- Public bundle generation now also rejects AuthLayout, private Login/Register and PrivateGuard/privateSession modules, in addition to the existing admin exclusions.

Verification passed:

- Existing focused auth checks: token persistence, cross-tab synchronization, both roles, missing/invalid tokens, 401/403 handling, network-error retention, malformed role responses, login token response shapes, identity races and query cache clearing.
- Route matching using React Router: every private shell path has its expected role guard; login/register remain outside those guards; evaluation redirects to models; unmatched private paths render empty without router errors. Public auth routes, annotator routes, numeric ids, catch-all 404s and exclusion of admin routes behave as intended.
- Public guard checks: loading/refetch blocks Outlet; failure preserves the full path/search/hash in the login next parameter; success permits Outlet; each navigation uses its own session query.
- All three layout CSS Modules match the source scoped CSS after whitespace normalization. Server-rendered AdminLayout markup retains the skip link, navigation destinations, annotation breadcrumb/current state and collapsed mobile-menu state. This was not a browser or responsive visual check.
- Public bundle gate accepts public modules and rejects all listed private modules using both Windows and POSIX paths. Generated JS excludes private shell/auth markers in public mode and contains them in private mode.
- npm run build, npm run build:public and npm run build:private all passed, including their strict TypeScript build step.

Phase 3 is complete. QueryClientProvider is mounted in both entry points; separate entry graphs register only their mode's routes. Vue/backend files and unrelated root changes were left untouched. No permanent test suite was added. Data-route page elements remain intentionally pending Phase 4; full browser/API and visual parity checks remain pending Phase 5.
