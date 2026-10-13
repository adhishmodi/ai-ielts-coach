import { expect, test } from "@playwright/test";

test.skip(Boolean(process.env.PLAYWRIGHT_BASE_URL), "Exam-mode interactions run only against the isolated CI database.");

test("exam mode locks a section recording after it ends", async ({ page }) => {
  const email = `exam-mode-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Exam Mode Test Learner");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });

  await page.goto("/listening");
  const testCard = page.locator(".test-card").filter({
    hasText: "Listening Practice 1: Everyday Conversations",
  });
  await expect(testCard).toBeVisible({ timeout: 15_000 });
  await testCard.getByRole("button", { name: "Exam mode" }).click();

  await expect(page.getByText(/Exam mode: one play-through per section/)).toBeVisible();
  const audio = page.locator("audio").first();
  await expect(audio).toHaveAttribute("src", /dialogue_2-01_ordering_a_meal/);

  // Dispatch media events to test the replay lock without relying on the external audio host.
  await audio.evaluate((element) => element.dispatchEvent(new Event("ended")));
  await expect(page.getByRole("button", { name: "Recording finished" })).toBeDisabled();

  await page.getByRole("button", { name: /Section 2/ }).click();
  await expect(page.getByRole("heading", { name: "Section 2: Transportation" })).toBeVisible();
  await page.getByRole("button", { name: /Section 1/ }).click();
  await expect(page.getByRole("button", { name: "Recording finished" })).toBeDisabled();
});
