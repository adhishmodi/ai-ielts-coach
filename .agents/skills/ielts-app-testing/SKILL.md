---
name: ielts-app-testing
description: Safely test the AI IELTS Coach application using pytest, Playwright, isolated CI databases, GitHub Actions, and read-only production smoke checks. Use when planning, implementing, debugging, or verifying tests for this repository.
---

# IELTS Coach Testing Skill

## Mission

Produce evidence-based confidence that the AI IELTS Coach works without risking user data or changing production behavior unintentionally. Prefer repeatable automated tests in GitHub Actions over manual/local testing. Use the existing test architecture before introducing new tools or workflows.

## Repository and stack

- Backend: FastAPI, async SQLAlchemy, PostgreSQL/asyncpg, Alembic, pytest.
- Frontend: Next.js, React, TypeScript, Playwright Test.
- Main workflows:
  - `.github/workflows/ci.yml`: backend tests/migrations and frontend production build.
  - `.github/workflows/browser-smoke.yml`: Playwright E2E against an isolated PostgreSQL service and a locally hosted API/frontend build.
  - `.github/workflows/production-browser-smoke.yml`: public-page smoke tests against a deployed URL.
- Browser tests live in `frontend/tests/e2e/`; Playwright configuration is `frontend/playwright.config.ts`.
- Backend fixtures and helpers live in `backend/tests/conftest.py`.
- CI E2E practice data is created by `backend/scripts/seed_e2e_practice.py`.

Always inspect these files and the current branch/commit before recommending changes. Paths and implementation can evolve; repository contents are authoritative.

## Operating rules

1. **Inspect before acting.** Read the relevant code, tests, workflows, recent commits, and actual Actions results before diagnosing a failure or proposing changes.
2. **Respect the requested scope.** Do not modify application code, database schema/data, CI configuration, secrets, Vercel settings, or production settings unless the user explicitly approved that category of change. Documentation-only requests should remain documentation-only unless a directly related CI defect blocks the requested outcome and the user authorized small CI improvements.
3. **Use GitHub Actions as the source of truth.** After a change, inspect the actual workflow run, job status, and relevant logs. A successful commit/push is not test evidence. If the available tools cannot trigger or retrieve a run, say so and provide the exact workflow URL or manual dispatch steps; never claim it passed.
4. **Do not use TinyFish.** Do not invoke TinyFish or paid browser agents unless the user explicitly authorizes it for that task. Prefer repository Playwright tests and GitHub Actions.
5. **No secrets in chat.** Never ask the user to paste passwords, JWT secrets, API keys, database URLs, cookies, or access tokens. Use repository/environment secrets and masked CI variables. Do not print secrets in logs or artifacts.
6. **Keep test data isolated.** Backend tests must use a dedicated test database. Browser E2E must use the isolated PostgreSQL service defined in `browser-smoke.yml`, run migrations, and seed deterministic fixture content. Never point destructive tests at production.
7. **Production smoke tests are read-only.** Treat a deployed app URL as an external system. Limit checks to public page loading, navigation, layout, and safe read-only endpoints. Do not create accounts, submit answers, trigger AI evaluations, send emails, mutate settings, or create attempts/drafts in production unless a separately approved safe test plan explicitly permits it. Never use the full E2E suite against production by default.
8. **Keep evidence and reporting precise.** Separate facts observed in source, test results, and hypotheses. Report commit SHA, workflow/run URL, job results, test totals when available, and any unverified areas. Include failure logs or trace/artifact links where useful.
9. **Make small, reversible changes.** Avoid unrelated refactors, dependency upgrades, schema changes, and broad rewrites. Preserve existing passing tests and working user flows.
10. **Do not claim success early.** A test is verified only when its result is visible in the actual runner output or GitHub Actions evidence. Distinguish queued, in progress, success, failure, skipped, and unavailable.

## Test layers and when to use them

### 1. Backend API and service tests

Use pytest for authentication, authorization, validation, business rules, persistence, scoring, and error handling.

- Reuse fixtures and helpers from `backend/tests/conftest.py`.
- Test both success and relevant failure paths.
- Verify persistence by reading saved records when the behavior promises persistence.
- Prefer deterministic mocked AI/provider responses for normal CI tests. Do not require a paid model API key for routine unit tests.
- Keep test cleanup inside the isolated test database.
- Apply Alembic migrations before testing schema-dependent behavior.

### 2. Frontend build and browser E2E

Use Playwright for user-visible flows that span pages, API calls, and persisted results.

- Add tests under `frontend/tests/e2e/` and follow existing selectors, fixtures, and test conventions.
- Prefer accessible roles/names and stable test IDs over brittle CSS selectors or arbitrary sleeps.
- Wait for meaningful UI state (response, saved result, score, feedback, or navigation), not just a click.
- Cover desktop and mobile where layout or interaction differs.
- Preserve Playwright failure diagnostics: trace, screenshot, video, and HTML report where configured.
- Do not run state-mutating E2E against a deployed URL. The current tests that create accounts, attempts, drafts, or submissions should run only against the isolated CI database.

### 3. Production smoke checks

Use `production-browser-smoke.yml` only for a deployment URL and its intended public-page checks.

- Check that the URL resolves, expected public page renders, and no fatal client-side error prevents use.
- Use the workflow's manual `base_url` input when a production deployment event did not start a run.
- Confirm the actual `PLAYWRIGHT_BASE_URL` is the intended deployed URL before running.
- Review the test file and Playwright configuration first; the external URL disables the local web server.
- A public-page smoke pass does not prove authentication, database writes, AI evaluation, or all four IELTS skills work in production.

## Existing commands and CI workflows

Run these only in the correct repository context and with environment variables pointing to isolated test services:

- Backend tests: `cd backend && python -m pytest -q`
- Apply migrations: `cd backend && alembic upgrade head`
- Show migration head: `cd backend && alembic current`
- Frontend build: `cd frontend && npm run build`
- Browser E2E: `cd frontend && npm run test:e2e`
- Install Chromium if needed: `cd frontend && npx playwright install --with-deps chromium`

The exact CI environment setup is in the workflows. Do not copy production environment variables into local or test configuration. The browser workflow builds the frontend with `NEXT_PUBLIC_API_URL` pointed at the isolated API and seeds deterministic E2E practice content before running the suite.

## Failure investigation workflow

1. Identify the exact commit and workflow run; verify the run is for the expected branch/SHA.
2. Read the failing job steps and logs. Download Playwright artifacts when present.
3. Classify the failure: application regression, flaky timing/selector, fixture/seed problem, environment/dependency issue, or unrelated infrastructure.
4. Reproduce with the narrowest relevant test against an isolated database if needed; never start by changing production or weakening assertions.
5. Make the smallest fix within the approved scope. Add/adjust a regression test when a real defect is found.
6. Run the relevant check and then the broader required CI suite. Check all jobs rather than relying on a single green job.
7. Verify the new commit's actual Actions results. If a workflow is still queued/in progress or results are inaccessible, report that state clearly.
8. Summarize root cause, files changed, test evidence, remaining risk, and next step.

## Coverage expectations

Use `docs/testing/coverage-matrix.md` as the living inventory. Update it when meaningful flows or automated coverage change. The matrix is an inventory, not a claim that every scenario is fully covered; confirm current test files and results before reporting coverage.

## CI changes

Prefer the existing workflows. Add a new job or alter workflow triggers only when there is a clear, directly related gap that cannot be handled by current jobs. Document the reason and expected effect separately. Never add production credentials or make CI tests write to production. Keep production smoke separate from the isolated full E2E suite.

## Completion report template

- **Scope:** what changed and what intentionally did not change.
- **Commit:** full SHA and GitHub link.
- **Validation:** workflow/run link; each relevant job's state; tests and totals if available.
- **Evidence:** relevant logs/artifacts and user-visible behavior confirmed.
- **Limitations:** tests skipped, unavailable tools, unverified production behaviors, or missing evidence.
- **Next step:** only the smallest logical follow-up; ask before expanding scope.
