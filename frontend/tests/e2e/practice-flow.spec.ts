import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `playwright-${Date.now()}-${Math.random().toString(36).slice(2, 10)}@example.com`;
}

async function createAccountThroughUi(page: Page) {
  const email = uniqueEmail();
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Playwright Test Learner");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Keep building your score." })).toBeVisible();
  return email;
}

test.describe("authenticated workflows (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "Never create accounts or practice attempts on a deployed database. Run this suite against the isolated PostgreSQL service in GitHub Actions.",
  );

  test("registration signs in and loads the learner dashboard", async ({ page }) => {
    await createAccountThroughUi(page);

    await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Reading", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Listening", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Writing", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Speaking", exact: true })).toBeVisible();
    await expect(page.getByText("Your first practice test is waiting.")).toBeVisible();
  });

  test("existing learner can sign in successfully", async ({ page }) => {
    const email = await createAccountThroughUi(page);
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Listening", exact: true })).toBeVisible();
  });


  test("expired access token refreshes and learner session continues", async ({ page }) => {
    await createAccountThroughUi(page);

    const originalRefreshToken = await page.evaluate(() => localStorage.getItem("refresh_token"));
    expect(originalRefreshToken).toBeTruthy();

    // Simulate access-token expiry without changing backend state. The real
    // isolated API must refresh the session and serve the retried request.
    await page.evaluate(() => localStorage.setItem("access_token", "expired-access-token"));
    const refreshResponsePromise = page.waitForResponse((response) =>
      response.url().includes("/auth/refresh") && response.request().method() === "POST",
    );

    await page.goto("/reading");
    const refreshResponse = await refreshResponsePromise;
    expect(refreshResponse.status()).toBe(200);

    await expect(page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Reading Test", exact: true }),
    })).toBeVisible({ timeout: 15_000 });

    const renewedTokens = await page.evaluate(() => ({
      access: localStorage.getItem("access_token"),
      refresh: localStorage.getItem("refresh_token"),
    }));
    expect(renewedTokens.access).toBeTruthy();
    expect(renewedTokens.access).not.toBe("expired-access-token");
    expect(renewedTokens.refresh).toBeTruthy();
    expect(renewedTokens.refresh).not.toBe(originalRefreshToken);
  });

  test("learner can complete a Listening practice attempt and review the score", async ({ page }) => {
    await createAccountThroughUi(page);
    await page.goto("/listening");

    const testCard = page.locator(".test-card").filter({
      hasText: "Listening Practice 1: Everyday Conversations",
    });
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Practice mode" }).click();

    await expect(page.getByRole("heading", { name: "Section 1: Ordering a Meal" })).toBeVisible();
    await page.getByLabel("Iced tea").check();
    await page.getByLabel("Well done").check();
    await page.getByLabel("Fish with potatoes and a salad").check();

    await page.getByRole("button", { name: /Section 2/ }).click();
    await expect(page.getByRole("heading", { name: "Section 2: Transportation" })).toBeVisible();
    await page.getByLabel("Taxis are hard to get during rush hour").check();
    await page.getByLabel("Ten minutes").check();

    await page.getByRole("button", { name: "Submit test" }).click();

    await expect(page.getByRole("heading", { name: "Your Listening review" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("5/5 correct")).toBeVisible();
    await expect(page.getByText("Estimated band")).toBeVisible();
    await expect(page.getByText("Why this is correct").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Back to tests" })).toBeVisible();
  });

  test("invalid login shows a useful error and does not sign in", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(uniqueEmail());
    await page.getByLabel("Password").fill("NotARealPassword123!");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.locator(".error-box")).toContainText("Invalid email or password", { timeout: 10_000 });
    await expect(page).toHaveURL(/\/login$/);
  });
});
