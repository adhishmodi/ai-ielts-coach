import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `mobile-writing-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
  }));
  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth);
}

async function waitForDraftSave(page: Page) {
  return page.waitForResponse((response) =>
    response.request().method() === "PUT" &&
    /\/writing\/attempts\/[^/]+\/tasks\/[^/]+$/.test(response.url()) &&
    response.status() === 200,
  );
}

test.describe("mobile Writing journey (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "This journey creates an account, attempt, and drafts; run only against the isolated PostgreSQL service in CI.",
  );

  test("learner can write both tasks, switch between drafts, and review at 390px", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/register");
    await page.getByLabel("Full name").fill("Mobile Writing Learner");
    await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
    await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });

    await page.goto("/writing");
    const testCard = page.locator(".test-card").first();
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await expectNoHorizontalOverflow(page);
    await expect(testCard.getByRole("button", { name: "Start test" })).toBeVisible();
    await testCard.getByRole("button", { name: "Start test" }).click();

    const editor = page.getByPlaceholder("Start writing here…");
    await expect(editor).toBeVisible();
    await expectNoHorizontalOverflow(page);

    // Mock only the external evaluator; attempt, draft, submission, and detail
    // persistence continue through the isolated CI API and PostgreSQL database.
    let evaluationCalls = 0;
    await page.route("**/writing/submissions/*/evaluate", async (route) => {
      evaluationCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          submission_id: `mobile-writing-submission-${evaluationCalls}`,
          status: "evaluated",
          evaluation: {
            id: `mobile-writing-evaluation-${evaluationCalls}`,
            task_response_band: 7,
            task_achievement_band: 7,
            coherence_band: 6.5,
            lexical_band: 7,
            grammar_band: 6.5,
            overall_band: 7,
            feedback: "Mobile Writing deterministic feedback.",
            strengths: ["Clear main ideas"],
            improvements: ["Add specific examples"],
            evaluated_by: "e2e-mock",
            evaluated_at: "2026-01-01T00:00:00Z",
          },
        }),
      });
    });

    const responses: Record<number, string> = {};
    for (const taskNumber of [1, 2]) {
      await page.getByRole("button", { name: new RegExp(`Task ${taskNumber}\\b`) }).click();
      const targetText = await page.locator(".word-target").innerText();
      const minimumWords = Number(targetText.match(/\d+/)?.[0]);
      expect(minimumWords).toBeGreaterThan(0);
      responses[taskNumber] = Array.from(
        { length: minimumWords + 5 },
        (_, index) => `task${taskNumber}word${index + 1}`,
      ).join(" ");

      const savedResponse = waitForDraftSave(page);
      await editor.fill(responses[taskNumber]);
      const saved = await savedResponse;
      expect((await saved.json()).word_count).toBe(minimumWords + 5);
      await expect(page.locator(".save-status")).toContainText(/^Saved\b/, { timeout: 10_000 });
      await expectNoHorizontalOverflow(page);
    }

    // Switching tasks must preserve the text entered in each editor.
    await page.getByRole("button", { name: /Task 1\b/ }).click();
    await expect(editor).toHaveValue(responses[1]);
    await page.getByRole("button", { name: /Task 2\b/ }).click();
    await expect(editor).toHaveValue(responses[2]);

    const submitButton = page.getByRole("button", { name: "Submit test" });
    await expect(submitButton).toBeVisible();
    await submitButton.click();
    await expect(page.getByRole("heading", { name: "Your Writing review" })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByText("Both tasks were submitted successfully.")).toBeVisible();
    await expect(page.getByText("Mobile Writing deterministic feedback.").first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.locator(".result-card .score")).toHaveText(["7", "7"]);
    expect(evaluationCalls).toBe(2);
    await expectNoHorizontalOverflow(page);
  });
});
