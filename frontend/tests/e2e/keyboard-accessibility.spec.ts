import { expect, test, type Locator, type Page } from "@playwright/test";

function uniqueEmail() {
  return `keyboard-a11y-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function registerLearner(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Keyboard Accessibility Learner");
  await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
}

async function tabUntilFocused(page: Page, target: Locator, maxTabs = 60) {
  for (let index = 0; index < maxTabs; index += 1) {
    if (await target.evaluate((element) => element === document.activeElement)) {
      await expect(target).toBeFocused();
      return;
    }
    await page.keyboard.press("Tab");
  }

  throw new Error(`Could not reach ${await target.toString()} using Tab within ${maxTabs} presses`);
}

test.describe("keyboard accessibility journeys (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "This journey registers an account and starts practice attempts; run only against isolated CI PostgreSQL.",
  );

  test("learner navigates dashboard and starts all four skills using the keyboard", async ({ page }) => {
    await registerLearner(page);

    const skills = [
      {
        name: "Reading",
        route: "/reading",
        cardAction: "Start test",
        activeHeading: "Passage 1",
        activeControl: () => page.getByPlaceholder("Type your answer").first(),
        inputText: "1998",
      },
      {
        name: "Listening",
        route: "/listening",
        cardAction: "Practice mode",
        activeHeading: "Section 1: Ordering a Meal",
        activeControl: () => page.getByLabel("Iced tea"),
        inputText: null,
      },
      {
        name: "Writing",
        route: "/writing",
        cardAction: "Start test",
        activeHeading: null,
        activeControl: () => page.getByPlaceholder("Start writing here…"),
        inputText: "A short response entered entirely with the keyboard.",
      },
      {
        name: "Speaking",
        route: "/speaking",
        cardAction: "Start speaking test",
        activeHeading: "Part 1",
        activeControl: () =>
          page.getByPlaceholder("Your transcript will appear here. You can edit it if needed…"),
        inputText: "I enjoy learning new skills and practising English.",
      },
    ];

    for (const skill of skills) {
      if (skill.name !== "Reading") {
        await page.goto("/");
        await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
      }

      const dashboardCard = page.locator(".dashboard-skill-card").filter({
        has: page.getByRole("heading", { name: skill.name, exact: true }),
      });
      await expect(dashboardCard).toBeVisible();
      await tabUntilFocused(page, dashboardCard);
      await expect
        .poll(() => dashboardCard.evaluate((element) => element.matches(":focus-visible")))
        .toBe(true);
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(new RegExp(`${skill.route.replace("/", "\\/")}$`));

      const startButton = page.getByRole("button", { name: skill.cardAction }).first();
      const testCard = page.locator(".test-card").filter({ has: startButton }).first();

      await expect(testCard).toBeVisible({ timeout: 15_000 });
      await tabUntilFocused(page, startButton);
      await expect
        .poll(() => startButton.evaluate((element) => element.matches(":focus-visible")))
        .toBe(true);
      await page.keyboard.press("Enter");

      if (skill.name === "Writing") {
        await expect(skill.activeControl()).toBeVisible();
      } else {
        await expect(page.getByRole("heading", { name: skill.activeHeading! })).toBeVisible();
      }

      // Speaking starts in a preparation phase. Keyboard-activate its explicit
      // transition before asserting focus on the transcript editor.
      if (skill.name === "Speaking") {
        const beginSpeakingButton = page.getByRole("button", { name: "Start speaking now" });
        await tabUntilFocused(page, beginSpeakingButton);
        await expect
          .poll(() => beginSpeakingButton.evaluate((element) => element.matches(":focus-visible")))
          .toBe(true);
        await page.keyboard.press("Enter");
        await expect(skill.activeControl()).toBeVisible();
      }

      const activeControl = skill.activeControl();
      await tabUntilFocused(page, activeControl);
      await expect(activeControl).toBeFocused();
      await expect
        .poll(() => activeControl.evaluate((element) => element.matches(":focus-visible")))
        .toBe(true);

      if (skill.name === "Listening") {
        await page.keyboard.press("Space");
        await expect(activeControl).toBeChecked();
      } else {
        await page.keyboard.type(skill.inputText!);
        await expect(activeControl).toHaveValue(skill.inputText!);
      }
    }
  });
});
