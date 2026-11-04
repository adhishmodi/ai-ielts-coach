import { expect, test, type Locator, type Page } from "@playwright/test";

function uniqueEmail() {
  return `keyboard-practice-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function registerLearner(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Keyboard Practice Learner");
  await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Your practice areas" })).toBeVisible();
}

async function tabUntilFocused(page: Page, target: Locator, maxTabs = 80) {
  for (let index = 0; index < maxTabs; index += 1) {
    if (await target.evaluate((element) => element === document.activeElement)) {
      await expect(target).toBeFocused();
      return;
    }
    await page.keyboard.press("Tab");
  }
  throw new Error(`Could not reach ${await target.toString()} using Tab within ${maxTabs} presses`);
}

async function selectRadioWithArrowKeys(page: Page, target: Locator) {
  const groupName = await target.getAttribute("name");
  expect(groupName).toBeTruthy();
  const radios = page.locator(`input[type="radio"][name="${groupName}"]`);
  const firstRadio = radios.first();
  await tabUntilFocused(page, firstRadio);
  const targetIndex = await target.evaluate((element) => {
    const group = Array.from(document.querySelectorAll<HTMLInputElement>('input[type="radio"]'))
      .filter((radio) => radio.name === (element as HTMLInputElement).name);
    return group.indexOf(element as HTMLInputElement);
  });
  const count = await radios.count();
  for (let index = 0; index < count && !(await target.isChecked()); index += 1) {
    await page.keyboard.press("ArrowDown");
  }
  await expect(target).toBeChecked();
  expect(targetIndex).toBeGreaterThanOrEqual(0);
}

async function activateWithKeyboard(page: Page, target: Locator, key: "Enter" | "Space" = "Enter", maxTabs = 80) {
  await tabUntilFocused(page, target, maxTabs);
  await expect.poll(() => target.evaluate((element) => element.matches(":focus-visible"))).toBe(true);
  await page.keyboard.press(key);
}

test.describe("keyboard-only practice task flows (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "These flows create accounts, attempts, and drafts; run only against isolated CI PostgreSQL.",
  );

  test("learner navigates Reading and Listening questions, Writing tasks, and Speaking parts by keyboard", async ({ page }) => {
    await registerLearner(page);

    // Reading: start a seeded attempt, answer question controls, and submit from keyboard.
    await page.goto("/reading");
    const readingCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Reading Test", exact: true }),
    });
    const readingStart = readingCard.getByRole("button", { name: "Start test" });
    await expect(readingCard).toBeVisible({ timeout: 15_000 });
    await activateWithKeyboard(page, readingStart);
    await expect(page.getByRole("heading", { name: "Passage 1" })).toBeVisible();

    const readingAnswer = page.getByPlaceholder("Type your answer").first();
    await tabUntilFocused(page, readingAnswer);
    await page.keyboard.type("1998");
    await expect(readingAnswer).toHaveValue("1998");

    const readingChoice = page.getByLabel("Central Library");
    await activateWithKeyboard(page, readingChoice, "Space");
    await expect(readingChoice).toBeChecked();

    const readingSubmit = page.getByRole("button", { name: "Submit test" });
    await activateWithKeyboard(page, readingSubmit);
    await expect(page.getByRole("heading", { name: "Your Reading review" })).toBeVisible({ timeout: 15_000 });

    // Listening: keyboard-select answers, move to Section 2, and submit.
    await page.goto("/listening");
    const listeningCard = page.locator(".test-card").filter({
      hasText: "Listening Practice 1: Everyday Conversations",
    });
    await expect(listeningCard).toBeVisible({ timeout: 15_000 });
    await activateWithKeyboard(page, listeningCard.getByRole("button", { name: "Practice mode" }));
    await expect(page.getByRole("heading", { name: "Section 1: Ordering a Meal" })).toBeVisible();

    const icedTea = page.getByLabel("Iced tea");
    await activateWithKeyboard(page, icedTea, "Space");
    await expect(icedTea).toBeChecked();

    const sectionTwo = page.getByRole("button", { name: /Section 2/ });
    await activateWithKeyboard(page, sectionTwo);
    await expect(page.getByRole("heading", { name: "Section 2: Transportation" })).toBeVisible();

    const taxiAnswer = page.getByLabel("Taxis are hard to get during rush hour");
    // Radio groups expose one Tab stop; move among options with arrow keys.
    await selectRadioWithArrowKeys(page, taxiAnswer);
    await expect(taxiAnswer).toBeChecked();
    await activateWithKeyboard(page, page.getByRole("button", { name: "Submit test" }));
    await expect(page.getByRole("heading", { name: "Your Listening review" })).toBeVisible({ timeout: 15_000 });

    // Writing: keyboard-switch between task tabs, type responses, and submit.
    await page.goto("/writing");
    const writingCard = page.locator(".test-card").first();
    await expect(writingCard).toBeVisible({ timeout: 15_000 });
    await activateWithKeyboard(page, writingCard.getByRole("button", { name: "Start test" }));

    let evaluationCalls = 0;
    await page.route("**/writing/submissions/*/evaluate", async (route) => {
      evaluationCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          submission_id: `keyboard-writing-submission-${evaluationCalls}`,
          status: "evaluated",
          evaluation: {
            id: `keyboard-writing-evaluation-${evaluationCalls}`,
            task_response_band: 7,
            task_achievement_band: 7,
            coherence_band: 6.5,
            lexical_band: 7,
            grammar_band: 6.5,
            overall_band: 7,
            feedback: "Keyboard Writing deterministic feedback.",
            strengths: ["Clear ideas"],
            improvements: ["Add examples"],
            evaluated_by: "e2e-mock",
            evaluated_at: "2026-01-01T00:00:00Z",
          },
        }),
      });
    });

    const writingEditor = page.getByPlaceholder("Start writing here…");
    for (const taskNumber of [1, 2]) {
      const taskTab = page.getByRole("button", { name: new RegExp(`Task ${taskNumber}\\b`) });
      await activateWithKeyboard(page, taskTab);
      const targetText = await page.locator(".word-target").innerText();
      const minimumWords = Number(targetText.match(/\d+/)?.[0]);
      expect(minimumWords).toBeGreaterThan(0);
      const response = Array.from({ length: minimumWords + 3 }, (_, index) => `task${taskNumber}word${index + 1}`).join(" ");
      await tabUntilFocused(page, writingEditor);
      await page.keyboard.type(response);
      await expect(writingEditor).toHaveValue(response);
      await expect(page.locator(".save-status")).toContainText(/^Saved\b/, { timeout: 10_000 });
    }

    await activateWithKeyboard(page, page.getByRole("button", { name: "Submit test" }));
    await expect(page.getByRole("heading", { name: "Your Writing review" })).toBeVisible({ timeout: 20_000 });
    expect(evaluationCalls).toBe(2);

    // Speaking: keyboard-transition from prep to transcript, save each part, and advance.
    await page.goto("/speaking");
    const speakingCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Speaking Test", exact: true }),
    });
    await expect(speakingCard).toBeVisible({ timeout: 15_000 });
    await activateWithKeyboard(page, speakingCard.getByRole("button", { name: "Start speaking test" }));

    let speakingEvaluationCalls = 0;
    await page.route("**/speaking/responses/*/evaluate", async (route) => {
      speakingEvaluationCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          response_id: `keyboard-speaking-response-${speakingEvaluationCalls}`,
          status: "evaluated",
          evaluation: {
            id: `keyboard-speaking-evaluation-${speakingEvaluationCalls}`,
            response_id: `keyboard-speaking-response-${speakingEvaluationCalls}`,
            fluency_band: 7,
            lexical_band: 7,
            grammar_band: 6.5,
            pronunciation_band: 6.5,
            overall_band: 7,
            feedback: "Keyboard Speaking deterministic feedback.",
            strengths: ["Clear organisation"],
            improvements: ["Add examples"],
            evaluated_by: "e2e-mock",
            evaluated_at: "2026-01-01T00:00:00Z",
          },
        }),
      });
    });

    const transcripts = [
      "I enjoy learning new skills because they help me solve problems.",
      "I would like to learn photography because it combines creativity and technology.",
      "Lifelong learning helps people adapt to changes and find new opportunities.",
    ];
    for (const partNumber of [1, 2, 3]) {
      await expect(page.getByRole("heading", { name: new RegExp(`Part ${partNumber}`) })).toBeVisible({ timeout: 15_000 });
      const startSpeaking = page.getByRole("button", { name: "Start speaking now" });
      if (await startSpeaking.isVisible().catch(() => false)) {
        await activateWithKeyboard(page, startSpeaking);
      }

      const transcript = page.getByPlaceholder("Your transcript will appear here. You can edit it if needed…");
      await tabUntilFocused(page, transcript);
      await page.keyboard.type(transcripts[partNumber - 1]);
      await expect(transcript).toHaveValue(transcripts[partNumber - 1]);

      const nextButton = page.getByRole("button", { name: partNumber === 3 ? "Finish test" : "Save & continue" });
      const savedResponse = page.waitForResponse((response) =>
        response.request().method() === "PUT" &&
        /\/speaking\/attempts\/[^/]+\/parts\/[^/]+$/.test(response.url()) &&
        response.status() === 200,
      );
      await activateWithKeyboard(page, nextButton);
      const saved = await savedResponse;
      expect((await saved.json()).transcript).toBe(transcripts[partNumber - 1]);
    }

    await expect(page.getByRole("heading", { name: "Your Speaking review" })).toBeVisible({ timeout: 20_000 });
    expect(speakingEvaluationCalls).toBe(3);
  });
});
