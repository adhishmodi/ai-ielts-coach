import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `cross-browser-${Date.now()}-${Math.random().toString(36).slice(2, 10)}@example.com`;
}

async function registerLearner(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Cross-browser E2E Learner");
  await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
}

test.describe("stateful cross-browser journeys (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "These journeys create accounts and practice attempts; run only against the isolated CI PostgreSQL service.",
  );

  test("authenticated session survives skill navigation and reload", async ({ page }) => {
    await registerLearner(page);

    const initialTokens = await page.evaluate(() => ({
      access: localStorage.getItem("access_token"),
      refresh: localStorage.getItem("refresh_token"),
    }));
    expect(initialTokens.access).toBeTruthy();
    expect(initialTokens.refresh).toBeTruthy();

    await page.goto("/reading");
    await expect(page.locator("header .muted").first()).toHaveText("Reading");
    await expect(page.locator(".test-card").first()).toBeVisible({ timeout: 20_000 });

    await page.reload();
    await expect(page).toHaveURL(/\/reading$/);
    await expect(page.locator("header .muted").first()).toHaveText("Reading");
    await expect(page.locator(".test-card").first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();

    const retainedTokens = await page.evaluate(() => ({
      access: localStorage.getItem("access_token"),
      refresh: localStorage.getItem("refresh_token"),
    }));
    expect(retainedTokens.access).toBe(initialTokens.access);
    expect(retainedTokens.refresh).toBe(initialTokens.refresh);
  });

  test("learner submits a seeded Reading attempt and verifies its persisted review data", async ({ page }) => {
    await registerLearner(page);
    await page.goto("/reading");

    const testCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Reading Test", exact: true }),
    });
    await expect(testCard).toBeVisible({ timeout: 20_000 });

    const startResponse = page.waitForResponse((response) =>
      response.request().method() === "POST" &&
      /\/reading\/tests\/[^/]+\/start$/.test(response.url()) &&
      response.status() === 200,
    );
    await testCard.getByRole("button", { name: "Start test" }).click();
    const startedAttempt = await startResponse.then((response) => response.json() as Promise<{ attempt_id: string }>);
    await expect(page.getByRole("heading", { name: "Passage 1" })).toBeVisible();

    const textAnswers = page.getByPlaceholder("Type your answer");
    await textAnswers.nth(0).fill("1998");
    await page.getByLabel("Central Library").check();
    const questionCards = page.locator(".question-card");
    await questionCards.nth(2).getByLabel("True", { exact: true }).check();
    await questionCards.nth(3).getByLabel("False", { exact: true }).check();
    await questionCards.nth(4).getByLabel("Yes", { exact: true }).check();
    await textAnswers.nth(1).fill("1998");
    await textAnswers.nth(2).fill("weekday");
    await questionCards.nth(7).getByLabel("1998", { exact: true }).check();

    await page.getByRole("button", { name: "Submit test" }).click();
    await expect(page.getByRole("heading", { name: "Your Reading review" })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByText("8/8 correct")).toBeVisible();
    await expect(page.getByRole("button", { name: "Back to tests" })).toBeVisible();

    // The review UI is intentionally held in component state, so a page reload
    // returns to the test list. Verify persistence through the authenticated API.
    await page.reload();
    await expect(page).toHaveURL(/\/reading$/);
    await expect(page.locator(".test-card").first()).toBeVisible({ timeout: 20_000 });

    const persistedAttempt = await page.evaluate(async (attemptId) => {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`/api/v1/reading/attempts/${attemptId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(`Attempt detail request failed: ${response.status}`);
      return response.json();
    }, startedAttempt.attempt_id);

    expect(persistedAttempt.attempt_id).toBe(startedAttempt.attempt_id);
    expect(persistedAttempt.score).toBe(8);
    expect(persistedAttempt.total_questions).toBe(8);
    expect(persistedAttempt.answers).toHaveLength(8);
    expect(persistedAttempt.answers.every((answer: { is_correct: boolean }) => answer.is_correct)).toBe(true);
  });
});
