# React route parity checklist

Phase 4 evidence: code reading plus synthetic Chrome checks using intercepted API fixtures. **Needs manual check** means live backend, real media or human verification has not been performed. N/A means the reference route has no corresponding operation; no edit/delete functionality was invented.

| Mode / route | Renders | Data loads | Create / edit / delete or route actions | Error state | Auth guard | Mode gating |
|---|---|---|---|---|---|---|
| Private/default `/` | verified-by-code-reading: empty admin Outlet | N/A | N/A | N/A | verified-by-code-reading + focused guard checks | verified-by-code-reading |
| Private/default `/dashboard` | synthetic browser + sampled Vue comparison | fixture queries; needs manual check live | Refresh: verified-by-code-reading | verified-by-code-reading | focused guard checks | public browser 404 + build exclusion |
| Private/default `/dataset` | synthetic browser at 3 widths + Vue comparison | fixture list/pool/participants; needs manual check live | Single-video create and ZIP preview/import: synthetic browser; participant create/retry: verified-by-code-reading; edit/delete N/A | synthetic empty/error states | focused guard checks | public browser 404 + build exclusion |
| Private/default `/dataset/:id/annotate` | synthetic browser at 3 widths + Vue comparison | fixture session; needs manual check real video | Save-next/completion: synthetic browser; clear, previous/next and seeking: verified-by-code-reading; real playback needs manual check | verified-by-code-reading | focused guard checks | absent in public route table |
| Private/default `/training` | synthetic browser at 3 widths + Vue comparison | fixture jobs/eligible datasets | Selection, help and submission: synthetic browser; polling/failure payload: verified-by-code-reading; live run needs manual check | running/failed/completed fixtures | focused guard checks | public browser 404 + build exclusion |
| Private/default `/evaluation` | verified-by-code-reading: redirects `/models` | N/A | Redirect only; separate Evaluation page remains unregistered | N/A | focused guard checks | absent from public route table |
| Private/default `/models` | synthetic browser at 3 widths + Vue comparison | fixture registry/state | Selection and activation blockers: synthetic browser; activation mutation: verified-by-code-reading, needs manual check live; create/edit/delete N/A | verified-by-code-reading | focused guard checks | public browser 404 + build exclusion |
| Private/default `/pilot-results` | synthetic browser at 3 widths + Vue comparison | fixture results; needs manual check live | Refresh: verified-by-code-reading; CRUD N/A | verified-by-code-reading | focused guard checks | public browser 404 + build exclusion |
| Private/default `/annotator` | synthetic browser | fixture shared list; needs manual check live | Dataset navigation: verified-by-code-reading; CRUD N/A | verified-by-code-reading | focused role-guard checks | public mode uses its own cookie guard |
| Private/default `/annotator/:id` | shared annotation page: verified-by-code-reading | same token-backed session service | shared annotation operations: verified-by-code-reading; needs manual check live | verified-by-code-reading | focused role-guard checks | public variant requires numeric id |
| Private/default `/login` | synthetic browser at 3 widths | token login/me: focused mocked checks; needs manual check live | Login response shapes/token persistence tested; actual credentials need manual check | verified-by-code-reading | deliberately outside private wrapper | excluded from public graph |
| Private/default `/register` | synthetic browser at 3 widths | verified-by-code-reading; needs manual check live | Registration payload: verified-by-code-reading | verified-by-code-reading | deliberately outside private wrapper | excluded from public graph |
| Private/default unmatched URL | verified-by-code-reading + memory-router check: blank | N/A | N/A | Preserves reference blank output | no page registered | public variant has visible 404 |
| Public `/` | synthetic browser redirect `/annotator` | N/A | Redirect only | N/A | destination cookie guard | separate public entry |
| Public `/annotator/login` | synthetic browser | CSRF/login: verified-by-code-reading; needs manual check actual cookie flow | Safe next validation and redirect: verified-by-code-reading | verified-by-code-reading | deliberately unguarded auth page | separate public entry |
| Public `/annotator/register` | synthetic browser | CSRF/register/login: verified-by-code-reading; needs manual check live invitation | Registration/login payloads: verified-by-code-reading | verified-by-code-reading | deliberately unguarded auth page | separate public entry |
| Public `/annotator` | synthetic browser | fixture list + cookie-session check; needs manual check live | Dataset selection: verified-by-code-reading | verified-by-code-reading | cookie guard exercised with fixture status | private routes not registered |
| Public `/annotator/:id` (numeric) | synthetic browser | fixture session | CSRF + two rating saves through completion: synthetic browser; clear/media need manual check | verified-by-code-reading | cookie guard before Outlet | numeric precheck + separate public entry |
| Public unmatched/non-numeric URL | synthetic browser 404 | N/A | N/A | Reference 404 heading and text | numeric precheck occurs before session guard | admin/private URLs return 404 |

Synthetic artifacts: [private checks](../docs/admin-react/phase4-checks.json), [public checks](../docs/admin-react/phase4-public-checks.json). No permanent test suite was added. No Phase 4 files have been staged or committed.


## Final build and supplemental checks

- Passed: npm run build, npm run build:public, npm run build:private, and final npx tsc -b. Public bundling passed the private-module gate; generated JS inspection found no private page content.
- Private synthetic run: 47 checks; public synthetic run: 13 checks; supplemental run: 12 checks. All completed without failed checks or runtime errors.
- Supplemental Chrome coverage includes all eight private page layouts at 1280 CSS px without page overflow, allowed model activation and refreshed active status, clearing a previously saved annotation, and admin/annotator sign-out removing the token and returning to login. Live-backend verification remains required for those operations despite this fixture coverage.
- All six sampled Vue/React geometry/typography/color comparisons in the final private run were identical. Private screens were checked at 360, 768, 1280 and 1440 CSS px; public screens were exercised at 360 px and annotation at 768 px.
- The private eager bundle triggers Vite's non-failing large-chunk advisory. No UI/chart dependency was added and no deployment configuration was changed.

Supplemental evidence: [extra checks](../docs/admin-react/phase4-extra-checks.json). No commits or staging were performed.
