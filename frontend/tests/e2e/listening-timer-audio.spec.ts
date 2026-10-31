import { expect, test, type Page } from "@playwright/test";

async function installFixture(
  page: Page,
  options: { startedAt?: string; timeLimitMinutes?: number; audioUrl?: string | null } = {},
) {
  const testData = {
    id: "listening-regression-test",
    title: "Listening Regression Test",
    description: "Deterministic timer and audio regression fixture",
    difficulty: "easy",
    time_limit_minutes: options.timeLimitMinutes ?? 40,
    sections: [{
      id: "regression-section",
      title: "Section 1: Regression Checks",
      instructions: "Answer the question.",
      audio_url: options.audioUrl ?? null,
      order: 1,
      questions: [{
        id: "regression-question",
        question_text: "Which answer should be selected?",
        question_type: "multiple_choice",
        options: ["Option A", "Option B"],
        order: 1,
      }],
    }],
  };
  let submissionCount = 0;

  await page.route("**/api/v1/listening/tests", (route) => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify([testData]),
  }));
  await page.route("**/api/v1/listening/tests/*/start", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      attempt_id: "attempt-listening-regression",
      listening_test_id: testData.id,
      started_at: options.startedAt ?? new Date().toISOString(),
    }),
  }));
  await page.route("**/api/v1/listening/attempts/attempt-listening-regression/submit", (route) => {
    submissionCount += 1;
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        attempt_id: "attempt-listening-regression", score: 0, total_questions: 1, band_score: 1,
      }),
    });
  });
  await page.route("**/api/v1/listening/attempts/attempt-listening-regression", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      attempt_id: "attempt-listening-regression",
      listening_test_id: testData.id,
      score: 0,
      total_questions: 1,
      band_score: 1,
      submitted_at: new Date().toISOString(),
      answers: [{
        question_id: "regression-question",
        question_text: "Which answer should be selected?",
        question_type: "multiple_choice",
        user_answer: "",
        correct_answer: "Option A",
        is_correct: false,
        explanation: "The fixture expects Option A.",
        section_title: "Section 1: Regression Checks",
      }],
    }),
  }));

  return { getSubmissionCount: () => submissionCount };
}

async function startFixture(page: Page) {
  await page.goto("/listening");
  const card = page.locator(".test-card").filter({ hasText: "Listening Regression Test" });
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Practice mode" }).click();
}

test("Listening automatically submits once when the timer has expired", async ({ page }) => {
  const fixture = await installFixture(page, {
    startedAt: new Date(Date.now() - 120_000).toISOString(),
    timeLimitMinutes: 1,
  });
  await startFixture(page);

  await expect(page.getByRole("heading", { name: "Your Listening review" })).toBeVisible({ timeout: 8_000 });
  await expect(page.getByText("0/1 correct").first()).toBeVisible();
  expect(fixture.getSubmissionCount()).toBe(1);
});

test("Listening reports an audio playback failure clearly", async ({ page }) => {
  await installFixture(page, { audioUrl: "https://example.com/test-audio.mp3" });
  await startFixture(page);

  const audio = page.locator("audio").first();
  await audio.evaluate((element) => {
    Object.defineProperty(element, "play", {
      configurable: true,
      value: () => Promise.reject(new Error("Playback blocked by test")),
    });
  });
  await page.getByRole("button", { name: "Play audio" }).click();
  await expect(page.locator(".floating-error")).toContainText(
    "Audio playback failed. Please check your connection and try again.",
  );
});

test("Listening practice mode allows replaying a finished recording from the beginning", async ({ page }) => {
  await installFixture(page, { audioUrl: "https://example.com/test-audio.mp3" });
  await startFixture(page);

  const audio = page.locator("audio").first();
  await audio.evaluate((element) => {
    Object.defineProperty(element, "currentTime", { configurable: true, writable: true, value: 42 });
    Object.defineProperty(element, "play", {
      configurable: true,
      value: () => {
        element.dispatchEvent(new Event("play"));
        return Promise.resolve();
      },
    });
  });

  await page.getByRole("button", { name: "Play audio" }).click();
  await expect(page.getByRole("button", { name: "Pause audio" })).toBeVisible();
  await audio.evaluate((element) => element.dispatchEvent(new Event("ended")));
  await expect(page.getByRole("button", { name: "Recording finished" })).toBeVisible();

  await page.getByRole("button", { name: "Recording finished" }).click();
  await expect(page.getByRole("button", { name: "Pause audio" })).toBeVisible();
  expect(await audio.evaluate((element) => element.currentTime)).toBe(0);
});


test("Listening displays an error and stays out of review when submission fails", async ({ page }) => {
  await installFixture(page);
  await startFixture(page);

  await page.route("**/api/v1/listening/attempts/attempt-listening-regression/submit", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Submission temporarily unavailable." }),
    }),
  );

  await page.getByRole("button", { name: "Submit test" }).click();
  await expect(page.locator(".floating-error")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("heading", { name: "Your Listening review" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Submit test" })).toBeVisible();
});
