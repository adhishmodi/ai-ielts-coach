import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `writing-eval-failure-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function registerLearner(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Writing Evaluation Failure Learner");
  await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
}

test.describe("Writing evaluation failure (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "This journey creates an account, attempt, and submissions; run only against isolated CI PostgreSQL.",
  );

  test("shows saved submissions without inventing scores when AI evaluation fails", async ({ page }) => {
    await registerLearner(page);
    await page.goto("/writing");

    const testCard = page.locator(".test-card").first();
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Start test" }).click();

    let evaluationCalls = 0;
    await page.route("**/writing/submissions/*/evaluate", async (route) => {
      evaluationCalls += 1;
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "AI evaluation temporarily unavailable." }),
      });
    });

    for (const taskNumber of [1, 2]) {
      await page.getByRole("button", { name: new RegExp(`Task ${taskNumber}\\b`) }).click();
      const targetText = await page.locator(".word-target").innerText();
      const minimumWords = Number(targetText.match(/\d+/)?.[0]);
      expect(minimumWords).toBeGreaterThan(0);

      const responseText = Array.from(
        { length: minimumWords + 5 },
        (_, index) => `failuretask${taskNumber}word${index + 1}`,
      ).join(" ");
      const saveResponse = page.waitForResponse((response) =>
        response.request().method() === "PUT" &&
        /\/writing\/attempts\/[^/]+\/tasks\/[^/]+$/.test(response.url()) &&
        response.status() === 200,
      );
      await page.getByPlaceholder("Start writing here…").fill(responseText);
      const saved = await saveResponse;
      expect((await saved.json()).word_count).toBe(minimumWords + 5);
      await expect(page.locator(".save-status")).toContainText(/^Saved\b/, { timeout: 10_000 });
    }

    await page.getByRole("button", { name: "Submit test" }).click();
    await expect(page.getByRole("heading", { name: "Your Writing review" })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByText("Both tasks were submitted successfully.")).toBeVisible();
    await expect(page.locator(".pending-box")).toHaveCount(2);
    await expect(page.getByText("AI evaluation is unavailable. The submission is saved.")).toHaveCount(2);
    await expect(page.locator(".overall-band strong")).toHaveText("—");
    await expect(page.locator(".result-card .score")).toHaveText(["—", "—"]);
    expect(evaluationCalls).toBe(2);
  });
});
