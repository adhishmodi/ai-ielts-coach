import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `a11y-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function registerLearner(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Accessibility Test Learner");
  await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
}

async function scanSeriousAccessibility(page: Page, screen: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const seriousOrCritical = results.violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  );
  expect(
    seriousOrCritical.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      description: violation.description,
      nodes: violation.nodes.map((node) => ({
        target: node.target,
        summary: node.failureSummary,
      })),
    })),
    `Serious/critical axe violations on ${screen}`,
  ).toEqual([]);
}

test.describe("accessibility baseline (isolated CI database only)", () => {
  test("login and registration have no serious or critical axe violations", async ({ page }) => {
    for (const route of ["/login", "/register"]) {
      await page.goto(route);
      await expect(page.locator("main")).toBeVisible();
      await scanSeriousAccessibility(page, route);
    }
  });

  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "This journey creates an account and practice attempt; run only against isolated CI PostgreSQL.",
  );

  test("dashboard and active Reading, Listening, Writing, and Speaking screens pass axe baseline", async ({ page }) => {
    await registerLearner(page);
    await scanSeriousAccessibility(page, "dashboard");

    await page.goto("/reading");
    const readingCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Reading Test", exact: true }),
    });
    await expect(readingCard).toBeVisible({ timeout: 15_000 });
    await readingCard.getByRole("button", { name: "Start test" }).click();
    await expect(page.getByRole("heading", { name: "Passage 1" })).toBeVisible();
    await scanSeriousAccessibility(page, "Reading active test");

    await page.goto("/listening");
    const listeningCard = page.locator(".test-card").filter({
      hasText: "Listening Practice 1: Everyday Conversations",
    });
    await expect(listeningCard).toBeVisible({ timeout: 15_000 });
    await listeningCard.getByRole("button", { name: "Practice mode" }).click();
    await expect(page.getByRole("heading", { name: "Section 1: Ordering a Meal" })).toBeVisible();
    await scanSeriousAccessibility(page, "Listening active test");

    await page.goto("/writing");
    const writingCard = page.locator(".test-card").first();
    await expect(writingCard).toBeVisible({ timeout: 15_000 });
    await writingCard.getByRole("button", { name: "Start test" }).click();
    await expect(page.getByPlaceholder("Start writing here…")).toBeVisible();
    await scanSeriousAccessibility(page, "Writing editor");

    await page.goto("/speaking");
    const speakingCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Speaking Test", exact: true }),
    });
    await expect(speakingCard).toBeVisible({ timeout: 15_000 });
    await speakingCard.getByRole("button", { name: "Start speaking test" }).click();
    await expect(page.getByRole("heading", { name: /Part 1/ })).toBeVisible();
    await scanSeriousAccessibility(page, "Speaking Part 1");
  });
});
