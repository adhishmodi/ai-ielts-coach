import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `skills-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function createAccountThroughUi(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Cross-skill Test Learner");
  await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
}

test.describe("Reading, Writing, and Speaking workflows (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "These workflows create attempts and drafts; run only against the isolated PostgreSQL service in GitHub Actions.",
  );

  test("Reading can start a test and submit to the answer review", async ({ page }) => {
    await createAccountThroughUi(page);
    await page.goto("/reading");

    const testCard = page.locator(".test-card").first();
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Start test" }).click();

    await expect(page.getByRole("heading", { name: /Passage 1|Reading/i }).first()).toBeVisible();
    // The API rejects empty submissions, so answer the deterministic seeded question first.
    await page.getByPlaceholder("Type your answer").fill("1998");
    await expect(page.getByPlaceholder("Type your answer")).toHaveValue("1998");
    await page.getByRole("button", { name: "Submit test" }).click();
    await expect(page.locator(".floating-error")).toBeHidden({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Your Reading review" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/correct$/).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Back to tests" })).toBeVisible();
  });

  test("Writing autosaves a draft as the learner types", async ({ page }) => {
    await createAccountThroughUi(page);
    await page.goto("/writing");

    const testCard = page.locator(".test-card").first();
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Start test" }).click();

    const editor = page.getByPlaceholder("Start writing here…");
    await expect(editor).toBeVisible();
    const draft =
      "The chart compares changes over time. Overall, the main trend is clear, although the categories differ in their rate of change.";
    const saveResponse = page.waitForResponse((response) =>
      response.request().method() === "PUT" &&
      /\/writing\/attempts\/[^/]+\/tasks\/[^/]+$/.test(response.url()) &&
      response.status() === 200,
    );
    await editor.fill(draft);
    const saved = await saveResponse;
    expect((await saved.json()).word_count).toBe(21);
    await expect(page.locator(".save-status")).toContainText(/^Saved\b/, { timeout: 10_000 });
    await expect(page.locator(".word-count")).toContainText(/\d+ words/);
  });

  test("Speaking saves a manually entered transcript and advances to Part 2", async ({ page }) => {
    await createAccountThroughUi(page);
    await page.goto("/speaking");

    // Select the deterministic fixture explicitly; other tests may be listed first by creation date.
    const testCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Speaking Test", exact: true }),
    });
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Start speaking test" }).click();

    await expect(page.getByRole("heading", { name: /Part 1/i })).toBeVisible({ timeout: 15_000 });
    // Assert the expected preparation phase before clicking, so a fixture mismatch fails clearly.
    const startSpeakingButton = page.getByRole("button", { name: "Start speaking now" });
    await expect(startSpeakingButton).toBeVisible({ timeout: 5_000 });
    await startSpeakingButton.click();

    const transcript = page.getByPlaceholder(
      "Your transcript will appear here. You can edit it if needed…",
    );
    await expect(transcript).toBeVisible();
    await transcript.fill(
      "I enjoy learning new skills because they help me solve problems. For example, I practise English regularly to prepare for my studies abroad.",
    );
    await page.getByRole("button", { name: "Save & continue" }).click();

    await expect(page.getByRole("heading", { name: /Part 2/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Response saved.")).toBeVisible();
  });
});
