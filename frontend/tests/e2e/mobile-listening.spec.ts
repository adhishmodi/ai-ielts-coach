import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `mobile-listening-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
  }));
  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth);
}

test.describe("mobile Listening journey (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "This journey creates an account and attempt; run only against the isolated PostgreSQL service in CI.",
  );

  test("learner can complete Listening and review answers at 390px", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/register");
    await page.getByLabel("Full name").fill("Mobile Listening Learner");
    await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
    await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });

    await page.goto("/listening");
    const testCard = page.locator(".test-card").filter({
      hasText: "Listening Practice 1: Everyday Conversations",
    });
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await expectNoHorizontalOverflow(page);
    const practiceButton = testCard.getByRole("button", { name: "Practice mode" });
    await expect(practiceButton).toBeVisible();
    await practiceButton.click();

    await expect(page.getByRole("heading", { name: "Section 1: Ordering a Meal" })).toBeVisible();
    await expect(page.getByLabel("Iced tea")).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.getByLabel("Iced tea").check();
    await page.getByLabel("Well done").check();
    await page.getByLabel("Fish with potatoes and a salad").check();

    const sectionTwoButton = page.getByRole("button", { name: /Section 2/ });
    await expect(sectionTwoButton).toBeVisible();
    await sectionTwoButton.click();
    await expect(page.getByRole("heading", { name: "Section 2: Transportation" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.getByLabel("Taxis are hard to get during rush hour").check();
    await page.getByLabel("Ten minutes").check();

    await expect(page.getByRole("button", { name: /Section 1/ })).toBeVisible();
    const submitButton = page.getByRole("button", { name: "Submit test" });
    await expect(submitButton).toBeVisible();
    await submitButton.click();

    await expect(page.getByRole("heading", { name: "Your Listening review" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("5/5 correct")).toBeVisible();
    await expect(page.getByRole("button", { name: "Back to tests" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
});
