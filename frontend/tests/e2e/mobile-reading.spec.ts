import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `mobile-reading-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
  }));
  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth);
}

test.describe("mobile Reading journey (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "This journey creates an account and attempt; run only against the isolated PostgreSQL service in CI.",
  );

  test("learner can complete Reading and review answers at 390px", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/register");
    await page.getByLabel("Full name").fill("Mobile Reading Learner");
    await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
    await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });

    await page.goto("/reading");
    const testCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Reading Test", exact: true }),
    });
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await expectNoHorizontalOverflow(page);
    const startButton = testCard.getByRole("button", { name: "Start test" });
    await expect(startButton).toBeVisible();
    await startButton.click();

    await expect(page.getByRole("heading", { name: "Passage 1" })).toBeVisible();
    await expect(page.locator(".passage-text")).toBeVisible();
    await expectNoHorizontalOverflow(page);

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

    await expect(textAnswers.nth(0)).toHaveValue("1998");
    const submitButton = page.getByRole("button", { name: "Submit test" });
    await expect(submitButton).toBeVisible();
    await submitButton.click();

    await expect(page.getByRole("heading", { name: "Your Reading review" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("8/8 correct")).toBeVisible();
    await expect(page.getByRole("button", { name: "Back to tests" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
});
