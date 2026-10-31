# IELTS Coach Test Coverage Matrix

This document inventories the current automated test strategy. A listed test layer means the workflow or test family is intended to exercise that area; it does **not** mean every edge case is covered or currently passing. Check the referenced test files and latest GitHub Actions run before making a status claim.

## Test environments

| Layer | Workflow / location | Environment | Allowed use |
|---|---|---|---|
| Backend API and service tests | `.github/workflows/ci.yml`, `backend/tests/` | Ephemeral PostgreSQL 16 service in GitHub Actions; migrations applied first | Authentication, API/service behavior, validation, persistence, regression tests |
| Frontend production build | `.github/workflows/ci.yml` | Node 20 build job | TypeScript/Next.js compilation and build-time checks |
| Full browser E2E | `.github/workflows/browser-smoke.yml`, `frontend/tests/e2e/` | Ephemeral PostgreSQL 16 database named `ielts_coach_e2e`, migrated and seeded; API and frontend built for CI | State-mutating end-to-end flows with disposable data |
| Deployed public-page smoke | `.github/workflows/production-browser-smoke.yml`, `frontend/tests/e2e/production-smoke.spec.ts` | Explicit deployed URL; no isolated database is attached | Read-only GET/navigation and rendering checks for public login and registration pages only |

## Feature coverage inventory

| Feature / risk | Backend/API tests | Playwright E2E | Production smoke | Notes / evidence to check |
|---|---|---|---|---|
| Registration and login | `backend/tests/test_auth_api.py`; shared `register` / `login` helpers in `backend/tests/conftest.py` | `frontend/tests/e2e/auth-pages.spec.ts` checks public forms; `frontend/tests/e2e/practice-flow.spec.ts` checks registration/dashboard, successful sign-in after sign-out, and invalid login | `production-smoke.spec.ts` checks login and registration forms render; it does not submit either form | Successful sign-in uses an account created in the isolated CI database. Never use real user credentials or expose passwords in logs |
| Session/token behavior | `backend/tests/test_auth_api.py` and `tests/backend/test_auth.py` cover successful refresh, revoked/invalid/expired refresh tokens, logout revocation, missing/invalid access tokens, and authenticated `/users/me` access/update | `practice-flow.spec.ts` simulates expired access tokens for both successful and rejected refreshes: verifies the real isolated API refresh succeeds, confirms a new access token is saved (the current API reuses the refresh token), and checks a rejected refresh clears both tokens and redirects to login | Not covered | Expired refresh is tested deterministically by moving the persisted session expiry into the past; token expiry behavior is backend-only |
| Reading | `tests/backend/test_reading_api.py` covers authenticated test retrieval, question options, answer-key hiding, and ordering; reading service/API tests cover scoring and submission behavior | `frontend/tests/e2e/other-skills.spec.ts` verifies successful 3/3 submission/review, a 503 failure (visible error; no false review success), and retrying that same attempt successfully against the isolated CI API/database | Not covered | E2E seed uses a fresh isolated CI PostgreSQL database; additional supported Reading question-type combinations remain a gap |
| Listening | API tests and seeded listening fixtures | `listening-question-types.spec.ts`, `listening-exam-mode.spec.ts`, `listening-timer-audio.spec.ts`, and `practice-flow.spec.ts` cover loading/empty states, supported question types, timer/audio behavior, submission failure feedback (error shown; no false review success), exam-mode recording lock, submission, and review | Not covered | Check the current Actions run for pass/fail; public smoke intentionally does not start an attempt |
| Writing | `backend/tests/test_writing_api.py` and `backend/tests/test_ai_writing.py` cover API submission/draft behavior and mocked evaluator validation/retry/error handling | `frontend/tests/e2e/other-skills.spec.ts` verifies draft autosave, submits both tasks, and checks the results page and feedback with deterministic mocked evaluation. Attempt creation, draft saves, submission, and attempt-detail reads use the isolated CI API/database | Not covered | Evaluation-provider behavior is mocked only for the browser journey; provider validation/retry/error cases remain in backend unit tests. Draft resume after reload is not supported by the current UI and is not claimed as covered |
| Speaking | API/service tests where present | `frontend/tests/e2e/other-skills.spec.ts` completes Parts 1–3 with manual transcripts, verifies each successful save and final persisted transcript, submits the attempt, and checks three deterministic evaluation results and feedback. Only the evaluator endpoint is mocked; attempt and response persistence use the isolated CI API/database | Not covered | Confirm this test passes in the full isolated Browser E2E workflow. Microphone capture and live speech recognition are intentionally excluded; evaluation-provider behavior remains covered separately where backend tests exist |
| Cross-skill navigation and dashboard | Inspect route/API tests | E2E tests cover selected authenticated flows; a loaded dashboard alone does not prove each skill works | Not covered | Keep mutating journeys confined to the isolated E2E environment |
| Results, review, and persistence | Listening, Reading, Writing, and Speaking API tests cover their respective attempt/answer/response/submission behavior where implemented | `practice-flow.spec.ts` verifies Listening score, estimated band, and explanation; `other-skills.spec.ts` verifies Reading review, the complete two-task Writing submission/results journey, and the full three-part Speaking submission/review with deterministic mocked evaluation feedback. Writing draft resume after reload is not supported and is not claimed as covered | Not covered | Browser evaluation is mocked, while attempt creation, draft/response persistence, submission, and attempt-detail reads remain on isolated CI services |
| Responsive/mobile layout | Unit/build checks where present | `auth-pages.spec.ts` checks the registration page at a 390px viewport | Not covered by production smoke | Browser configuration currently defines Chromium Desktop Chrome; explicit mobile projects may need separate scope approval |
| Error and empty states | API validation/error tests | Listening E2E asserts loading/empty states and audio playback failure; other specs assert invalid-login feedback | Not covered by production smoke | Avoid brittle assertions on implementation-specific error strings |
| Database migration safety | `alembic upgrade head` and `alembic current` in CI | E2E workflow migrates its isolated database before seeding | Never run migrations against production as part of smoke testing | Schema changes require migration review and a dedicated test |
| AI evaluation/provider failures | Test mocked failure/timeout and persisted result behavior where covered | Verify user-visible handling and no false success when API fails | Not covered | No API key should be required for routine CI; production evaluation needs separate approved verification |
| Email/external integrations | Unit/API tests with mocks where present | Do not send real email during CI | Never trigger from public smoke | Use test doubles and assert intended payloads |

## Current known Playwright suite and workflow behavior

- Playwright test directory: `frontend/tests/e2e/` contains 25 tests across seven spec files: `auth-pages.spec.ts`, `listening-exam-mode.spec.ts`, `listening-question-types.spec.ts`, `listening-timer-audio.spec.ts`, `other-skills.spec.ts`, `practice-flow.spec.ts`, and `production-smoke.spec.ts`. Verify the current Actions run for pass/fail status.
- Configuration: `frontend/playwright.config.ts`.
- CI browser project: Chromium with retry enabled in CI; traces, screenshots, and video are retained on failures according to config.
- The isolated browser workflow applies Alembic migrations, runs `backend/scripts/seed_e2e_practice.py`, starts FastAPI against its test PostgreSQL service, builds the frontend with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1`, and runs `npm run test:e2e`. This suite may mutate data and must stay pointed at disposable CI data.
- The production smoke workflow runs only `npx playwright test tests/e2e/production-smoke.spec.ts`. These tests navigate to the public login and registration pages and assert visible form elements; they do not submit forms, sign in, create accounts, start practice attempts, or save drafts.
- Do not set `PLAYWRIGHT_BASE_URL` to a production URL when running the full state-mutating E2E suite. The production workflow's dedicated spec is the only suite intended for deployed read-only checks.
- Failure diagnostics are uploaded as workflow artifacts when the corresponding job fails.

## Updating this matrix

When changing test coverage:

1. Link the exact test file(s) and describe the assertion that proves the behavior.
2. Distinguish API/service tests from end-to-end browser tests.
3. Note whether the test uses isolated fixtures, mocked external services, or live dependencies.
4. Record gaps honestly; do not infer coverage from a route existing or from a successful build.
5. Use actual GitHub Actions results for pass/fail status. Do not store transient status such as “currently green” as a permanent coverage fact.
