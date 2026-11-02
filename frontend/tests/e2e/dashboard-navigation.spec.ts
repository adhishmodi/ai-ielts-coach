import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `dashboard-navigation-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function registerLearner(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Navigation Test Learner");
  await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
}

test.describe("cross-skill dashboard navigation (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "This journey registers an account; run only against the isolated PostgreSQL service in CI.",
  );

  test("learner navigates dashboard to all four skills and returns without losing the session", async ({ page }) => {
    await registerLearner(page);

    const skills = [
      { name: "Reading", route: "/reading" },
      { name: "Listening", route: "/listening" },
      { name: "Writing", route: "/writing" },
      { name: "Speaking", route: "/speaking" },
    ];

    for (const skill of skills) {
      const card = page.locator(".dashboard-skill-card").filter({
        has: page.getByRole("heading", { name: skill.name, exact: true }),
      });
      await expect(card).toBeVisible();
      await card.click();

      await expect(page).toHaveURL(new RegExp(`\\${skill.route.replace("/", "\\/")}$`));
      await expect(page.locator("header .muted").first()).toHaveText(skill.name);
      await expect(page.locator(".test-card").first()).toBeVisible({ timeout: 15_000 });

      await page.goBack();
      await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
      await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
      await expect(page.getByRole("heading", { name: skill.name, exact: true })).toBeVisible();
    }
  });
});
