# IELTS Coach Test Coverage Matrix

This document inventories the current automated test strategy. A listed test layer means the workflow or test family is intended to exercise that area; it does **not** mean every edge case is covered or currently passing. Check the referenced test files and latest GitHub Actions run before making a status claim.

## Test environments

| Layer | Workflow / location | Environment | Allowed use |
|---|---|---|---|
| Backend API and service tests | `.github/workflows/ci.yml`, `backend/tests/` | Ephemeral PostgreSQL 16 service in GitHub Actions; migrations applied first | Authentication, API/service behavior, validation, persistence, regression tests |
| Frontend production build | `.github/workflows/ci.yml` | Node 20 build job | TypeScript/Next.js compilation and build-time checks |
| Full browser E2E | `.github/workflows/browser-smoke.yml`, `frontend/tests/e2e/` | Ephemeral PostgreSQL 16 database named `ielts_coach_e2e`, migrated and seeded; API and frontend built for CI | State-mutating end-to-end flows with disposable data |
| Deployed public-page smoke | `.github/workflows/production-browser-smoke.yml` | Explicit deployed URL; no isolated database is attached | Public-page availability/rendering only; read-only checks |

## Feature coverage inventory

| Feature / risk | Backend/API tests | Playwright E2E | Production smoke | Notes / evidence to check |
|---|---|---|---|---|
| Registration and login | `backend/tests/test_auth_api.py`; shared `register` / `login` helpers in `backend/tests/conftest.py` | `frontend/tests/e2e/auth-pages.spec.ts` checks public forms; `frontend/tests/e2e/practice-flow.spec.ts` checks registration/dashboard, successful sign-in after sign-out, and invalid login | Public login page only; no credentialed production sign-in | Successful sign-in uses an account created in the isolated CI database. Never use real user credentials or expose passwords in logs |
| Session/token behavior | Check auth, refresh, logout and protected-route test modules | Usually exercised indirectly by authenticated flows | Not proven by public smoke | Confirm token expiry/invalid-token edge cases in current test modules |
| Reading | API tests and seeded reading fixtures | Recent E2E coverage for Reading test selection, answering/submission, and result UI; verify exact assertions in current test files | Not proven by public smoke | E2E content seeded only in isolated CI database |
| Listening | API tests and seeded listening fixtures | Listening practice/exam-mode tests exist; inspect current test files for audio controls, timer, question types, submission, and review | Not proven by public smoke | Check audio asset availability and supported question types explicitly |
| Writing | `backend/tests/test_writing_api.py` and `backend/tests/test_ai_writing.py` cover API submission/draft behavior and mocked evaluator validation/retry/error handling | `frontend/tests/e2e/other-skills.spec.ts` verifies a successful draft PUT response (`word_count`) and the UI's definitive `Saved` state. Full browser submission/evaluation is not covered by this spec | Not proven by public smoke | Current UI starts an attempt in component state and does not restore an in-progress attempt after a page reload. Draft persistence is verified through the successful save response, not resume-after-reload. AI/provider tests should remain deterministic in CI |
| Speaking | API/service tests where present | Recent E2E coverage for speaking transcript/flow and preparation timer behavior | Not proven by public smoke | Check permission for microphone-related behavior; avoid tests requiring a real microphone where mocked input suffices |
| Cross-skill navigation and dashboard | Inspect route/API tests | E2E tests can verify entry points and navigation across four skills | Only pages reachable without mutation | A loaded dashboard alone does not prove each skill works |
| Results, review, and persistence | Listening, Reading, and Writing API tests verify attempt/answer/submission records and review details in their respective `backend/tests/test_*_api.py` modules | `practice-flow.spec.ts` verifies Listening score, estimated band, and explanation; `other-skills.spec.ts` verifies the Writing draft save acknowledgement. Draft resume after reload is not currently supported by the Writing page and is not claimed as covered | Not proven by public smoke | Prefer checking a saved record or stable result UI, not only success toast |
| Responsive/mobile layout | Unit/build checks where present | Add viewport-specific assertions for important layouts/interactions | Public pages only if safe | Browser configuration currently defines Chromium Desktop Chrome; explicit mobile projects may need separate scope approval |
| Error and empty states | API validation/error tests | Assert meaningful error messages and empty/loading states where reliable | Public availability only | Avoid brittle assertions on implementation-specific error strings |
| Database migration safety | `alembic upgrade head` and `alembic current` in CI | E2E workflow migrates its isolated database before seeding | Never run migrations against production as part of smoke testing | Schema changes require migration review and a dedicated test |
| AI evaluation/provider failures | Test mocked failure/timeout and persisted result behavior where covered | Verify user-visible handling and no false success when API fails | Not proven by public smoke | No API key should be required for routine CI; production evaluation needs separate approved verification |
| Email/external integrations | Unit/API tests with mocks where present | Do not send real email during CI | Never trigger from public smoke | Use test doubles and assert intended payloads |

## Current known Playwright suite and workflow behavior

- Playwright test directory: `frontend/tests/e2e/` (17 tests across `auth-pages.spec.ts`, `practice-flow.spec.ts`, `other-skills.spec.ts`, and `listening-exam-mode.spec.ts`; verify the current Actions run for pass/fail status).
- Configuration: `frontend/playwright.config.ts`.
- CI browser project: Chromium with retry enabled in CI; traces, screenshots, and video are retained on failures according to config.
- The isolated browser workflow applies Alembic migrations, runs `backend/scripts/seed_e2e_practice.py`, starts FastAPI against its test PostgreSQL service, builds the frontend with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1`, and runs `npm run test:e2e`.
- The production smoke workflow uses `PLAYWRIGHT_BASE_URL` and is intentionally separate. The existing E2E suite contains state-mutating tests and should not be treated as production-safe merely because the external base URL can be set.
- Failure diagnostics are uploaded as workflow artifacts when the corresponding job fails.

## Updating this matrix

When changing test coverage:

1. Link the exact test file(s) and describe the assertion that proves the behavior.
2. Distinguish API/service tests from end-to-end browser tests.
3. Note whether the test uses isolated fixtures, mocked external services, or live dependencies.
4. Record gaps honestly; do not infer coverage from a route existing or from a successful build.
5. Use actual GitHub Actions results for pass/fail status. Do not store transient status such as “currently green” as a permanent coverage fact.
