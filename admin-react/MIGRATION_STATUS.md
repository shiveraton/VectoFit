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

Phase 0 audit; Phase 1 strict TypeScript/Vite React scaffold; Phase 2 copied services, contracts, constants, assets and Axios clients; Phase 3 routing/auth shell, layouts and authentication pages; Phase 4 all page/component ports and route wiring. All 49 Vue components have TSX counterparts in admin-react. Vue and Django source files have no changes.

## Remaining work

The React implementation now contains all registered pages and all reference components, with React Query hooks and CSS Modules. Real-backend integration, real video playback, native keyboard/screen-reader verification, and production deployment cutover remain to be checked. PARITY_CHECKLIST.md distinguishes code reading and synthetic browser evidence from these remaining manual checks.

## Actual verification

- Empty-shell `npm run build`: passed before Phase 1 commit.
- Auth-shell `npm run build`: passed.
- `npx tsc -b`, `npm run build:private`, `npm run build:public`: passed after auth changes.
- Public bundle generation passed its module-exclusion check. Built JS inspection confirmed absence of private guard text, private login text and admin portal content from public output, and presence of private guard text in private output.
- No Vue/Pinia/vue-router imports in React source.
- Ephemeral verification (TypeScript transpilation, actual Zustand state, mocked HTTP/query/router boundaries): passed token persistence, normalization, both roles, missing tokens, 401/403 rejection, network failure retention, malformed role response, login response shapes, identity races, cache cancellation/clearing, cross-tab logout and guard render decisions.
- At the end of Phase 3, no browser/visual or live backend verification had been performed. Phase 4 synthetic browser evidence is recorded below; live backend checks remain pending. No test suite was added.

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

For public-mode comparison, use `npm run dev:public` in each directory with the same respective port arguments. Both applications now expose their full reference page set for comparison. The Vue application is retained as the unchanged reference.

## Phase 2 revalidation — 2026-11-06

Rechecked the existing Phase 2 implementation on request; no source-layer omissions or unintended rewrites were found.

- SHA-256 comparison: 19 files are byte-identical to the Vue reference: eight service modules (including their types, interfaces and local constants), seven files under src/assets (including the shared stylesheets), two public assets, config/publicAuth.ts and training/configuration/trainingParameters.ts.
- config/client.ts matches the reference after normalizing line endings and applying only the required getAuthToken import/accessor substitution. Its MODE branches, base URL precedence, endpoints, authorization format and header fallback remain intact. The accessor reads Zustand getState(), not a React hook.
- Local Axios adapter verification passed for development, production, public and private modes: default base URLs, both VITE URL overrides, token changes between requests, missing-token behavior, public-mode token suppression, AxiosHeaders and plain-object header handling. No HTTP requests were sent.
- npm run build passed (strict TypeScript project build followed by Vite).
- No Vue, Pinia or vue-router imports were found in the copied services/configuration. Vue-specific hooks, focus composables and routing remain outside the framework-neutral copy phase. Formatters embedded in those Vue modules require porting with their consumers; they are not standalone source modules that can be copied as-is.
- Vue and Django source files remain unchanged. No new dependencies or permanent test suite were added during this revalidation.

Phase 2 is complete. This Phase 2 revalidation preceded the Phase 4 implementation recorded below.

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

Phase 3 is complete. QueryClientProvider is mounted in both entry points; separate entry graphs register only their mode's routes. Vue/backend files and unrelated root changes were left untouched. No permanent test suite was added. This Phase 3 check preceded the Phase 4 implementation and synthetic browser comparisons below. Live API and manual accessibility checks remain pending.


## Phase 4 — complete, left uncommitted at the user's request

The follow-up instruction supersedes the original per-page commit requirement: no Phase 4 changes have been staged or committed.

- All 49 reference .vue files have .tsx counterparts, including App, layouts, authentication, every registered data page, shared components, the unregistered evaluation components, and null equivalents for the originally empty Users/Settings/Participants files. No new routes were created for unregistered source components. The existing unused evaluation demo retains its source-only simulated behavior; it is not reachable through the router, whose evaluation path still redirects to Models.
- Every registered data route now renders its React page. This is a native React port, not an SFC extension rename: controlled forms, callback props, local useState/useRef state, effects with cleanup, React Query queries/mutations, and centralized query keys replace the Vue runtime. The training draft uses Zustand only for client configuration. Copied API contracts and endpoint shapes remain unchanged.
- Dataset workflows retain single-video creation/validation, participant creation, processing retry/polling, ZIP preview/stratified or manual review selection, import outcomes, and annotation activity. Training retains FPPA v2 eligibility/filtering, fixed features/algorithm, hyperparameter controls, job polling, selected-run evidence, backend error payloads and model invalidation. Model evidence retains class mappings, metric availability, provenance, blockers and activation eligibility.
- Annotation retains grade precedence, direction resets, saved/inherited/unreviewed distinctions, sparse-save playback metadata, save-next wraparound, completion/review/clear, per-rep seeking and speed controls. Dialogs preserve focus containment/restoration, scroll lock, Escape and busy-state dismissal rules. Small native React transitions retain the existing help/dialog fade classes.
- Scoped CSS is in colocated CSS Modules. Generated component scope attributes preserve bare-element selector scope and specificity; native links/child roots forward their parent scope attributes. Shared original layout class names remain alongside module names so the reference global descendant rules still apply. No Vue compiler/runtime dependency was added to the React package; the one-off conversion aid was local tooling only.

Actual verification:

- All 49 counterpart files exist; no .vue files or Vue/Pinia/vue-router imports remain in React source. The inherited loose evaluation dataset type was narrowed to unknown; React source contains no any types.
- The default, public and private builds run the strict TypeScript project check. Full-mode build results and the detailed route checklist are recorded in PARITY_CHECKLIST.md.
- Synthetic Chrome run: 47 checks, zero failed checks and zero runtime/console errors. Eight private pages rendered at 1440, 768 and 360 CSS px without horizontal page overflow. The annotator home, model-version selection, activation blockers, dialog focus/Escape, ZIP preview and commit, single-video create, training submission/help, and annotation completion were exercised against intercepted fixture responses. Dataset empty/error and training running/failed/completed states were rendered.
- Vue/React comparisons at 1440 CSS px had identical sampled heading/section/card positions, dimensions, font sizes and colors for dashboard, datasets, training, models, pilot results and annotation. Screenshots and JSON evidence are in ../docs/admin-react/. This is sampled fixture-based parity, not a claim of pixel identity for every state.
- A separate public-mode browser run exercised root redirect, both auth pages, annotator home/session, numeric-id validation, private-route 404s, CSRF initialization and public rating saves through completion, with no runtime errors.
- All 25 bilateral grade combinations match source precedence. Sparse-save response merging preserves the original video object and FPS when the server returns only an id/null.
- No live backend was called during browser checks; API calls were intercepted. Real uploads/processing, activation, cookie/session configuration, playable media, actual keyboard/screen-reader use and production hosting still need manual integration verification.

The approved token/role guards and consistent private sign-out remain the intentional behavior changes from Vue. The private bundle currently retains eager page loading, as in the source, and Vite reports a large-chunk advisory. Production hosting/deployment was not switched.


Final Phase 4 supplemental verification: all three production build scripts and final npx tsc -b passed. The 47 private, 13 public and 12 supplemental synthetic checks had no failures/runtime errors. The supplemental run verified 1280px layouts, permitted activation, clearing a saved annotation and both private sign-outs. All six final sampled Vue/React layout comparisons were identical. See PARITY_CHECKLIST.md for the precise evidence and remaining live integration checks. All Phase 4 work remains unstaged and uncommitted; HEAD is still d1e80cd.
