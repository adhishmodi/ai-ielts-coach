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

  test("Reading supports short-answer, multiple-choice, and true/false answers through review", async ({ page }) => {
    await createAccountThroughUi(page);
    await page.goto("/reading");

    const testCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Reading Test", exact: true }),
    });
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Start test" }).click();

    await expect(page.getByRole("heading", { name: "Passage 1" })).toBeVisible();
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
    await expect(page.getByLabel("Central Library")).toBeChecked();
    await expect(textAnswers.nth(1)).toHaveValue("1998");
    await expect(textAnswers.nth(2)).toHaveValue("weekday");

    await page.getByRole("button", { name: "Submit test" }).click();
    await expect(page.locator(".floating-error")).toBeHidden({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Your Reading review" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("8/8 correct")).toBeVisible();
    await expect(page.locator(".review-question .question-type")).toHaveText([
      "Short Answer",
      "Multiple Choice",
      "True False",
      "True False Not Given",
      "Yes No Not Given",
      "Sentence Completion",
      "Summary Completion",
      "Matching",
    ]);
    for (const answer of ["1998", "Central Library", "True", "False", "Yes", "weekday"]) {
      await expect(page.locator(".answer-row").filter({ hasText: answer }).first()).toBeVisible();
    }
    await expect(page.getByRole("button", { name: "Back to tests" })).toBeVisible();
  });

  test("Reading submission failure shows an error and does not enter review", async ({ page }) => {
    await createAccountThroughUi(page);
    await page.goto("/reading");

    const testCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Reading Test", exact: true }),
    });
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Start test" }).click();
    await expect(page.getByRole("heading", { name: "Passage 1" })).toBeVisible();
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

    let submitRequests = 0;
    await page.route("**/reading/attempts/*/submit", async (route) => {
      submitRequests += 1;
      if (submitRequests === 1) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Reading submission temporarily unavailable." }),
        });
        return;
      }
      await route.continue();
    });

    const submitButton = page.getByRole("button", { name: "Submit test" });
    await submitButton.click();
    await expect(page.locator(".floating-error")).toContainText(
      "Reading submission temporarily unavailable.",
      { timeout: 10_000 },
    );
    await expect(page.getByRole("heading", { name: "Your Reading review" })).toHaveCount(0);
    await expect(submitButton).toBeVisible();

    // Retry the same attempt after the transient failure; the second request reaches
    // the isolated API and must complete normally rather than leaving a dead-end state.
    await submitButton.click();
    await expect(page.getByRole("heading", { name: "Your Reading review" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("8/8 correct")).toBeVisible();
    expect(submitRequests).toBe(2);
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


  test("Writing submits both tasks and displays deterministic evaluation feedback", async ({ page }) => {
    await createAccountThroughUi(page);
    await page.goto("/writing");

    const testCard = page.locator(".test-card").first();
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Start test" }).click();

    // Mock only the evaluation provider endpoint. Attempt creation, draft saves,
    // submission, and persisted attempt details still use the isolated CI API/database.
    let evaluationCalls = 0;
    await page.route("**/writing/submissions/*/evaluate", async (route) => {
      evaluationCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          submission_id: "e2e-submission-" + evaluationCalls,
          status: "evaluated",
          evaluation: {
            id: "e2e-evaluation-" + evaluationCalls,
            task_response_band: 7,
            task_achievement_band: 7,
            coherence_band: 6.5,
            lexical_band: 7,
            grammar_band: 6.5,
            overall_band: 7,
            feedback: "Deterministic E2E evaluation feedback.",
            strengths: ["Clear main ideas"],
            improvements: ["Develop supporting examples"],
            evaluated_by: "e2e-mock",
            evaluated_at: "2026-01-01T00:00:00Z",
          },
        }),
      });
    });

    for (const taskNumber of [1, 2]) {
      const taskTab = page.getByRole("button", { name: new RegExp("Task " + taskNumber + "\\b") });
      await taskTab.click();
      const targetText = await page.locator(".word-target").innerText();
      const minimumWords = Number(targetText.match(/\d+/)?.[0]);
      expect(minimumWords).toBeGreaterThan(0);

      const editor = page.getByPlaceholder("Start writing here…");
      const responseText = Array.from(
        { length: minimumWords + 5 },
        (_, index) => "word" + (index + 1),
      ).join(" ");
      const saveResponse = page.waitForResponse((response) =>
        response.request().method() === "PUT" &&
        /\/writing\/attempts\/[^/]+\/tasks\/[^/]+$/.test(response.url()) &&
        response.status() === 200,
      );
      await editor.fill(responseText);
      const saved = await saveResponse;
      expect((await saved.json()).word_count).toBe(minimumWords + 5);
      await expect(page.locator(".save-status")).toContainText(/^Saved\b/, { timeout: 10_000 });
    }

    await page.getByRole("button", { name: "Submit test" }).click();
    await expect(page.getByRole("heading", { name: "Your Writing review" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Both tasks were submitted successfully.")).toBeVisible();
    await expect(page.getByText("Deterministic E2E evaluation feedback.").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Clear main ideas").first()).toBeVisible();
    await expect(page.getByText("Develop supporting examples").first()).toBeVisible();
    await expect(page.locator(".score").filter({ hasText: "7" })).toHaveCount(2);
    expect(evaluationCalls).toBe(2);
  });

  test("Speaking completes all three parts and displays deterministic evaluation results", async ({ page }) => {
    await createAccountThroughUi(page);

    // Keep this journey independent of physical microphones and speech-recognition support.
    await page.addInitScript(() => {
      if (navigator.mediaDevices?.getUserMedia) {
        Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
          configurable: true,
          value: async () => {
            throw new Error("Microphone intentionally unavailable in this deterministic E2E test.");
          },
        });
      }
    });
    await page.goto("/speaking");

    // Select the deterministic fixture explicitly; other tests may be listed first by creation date.
    const testCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Speaking Test", exact: true }),
    });
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Start speaking test" }).click();

    // Only evaluation is mocked. Starting, saving, submitting, and reading the attempt
    // continue through the isolated CI API and PostgreSQL database.
    let evaluationCalls = 0;
    await page.route("**/speaking/responses/*/evaluate", async (route) => {
      evaluationCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          response_id: "e2e-speaking-response-" + evaluationCalls,
          status: "evaluated",
          evaluation: {
            id: "e2e-speaking-evaluation-" + evaluationCalls,
            response_id: "e2e-speaking-response-" + evaluationCalls,
            fluency_band: 7,
            lexical_band: 7,
            grammar_band: 6.5,
            pronunciation_band: 6.5,
            overall_band: 7,
            feedback: "Deterministic Speaking evaluation feedback.",
            strengths: ["Ideas are clearly organised"],
            improvements: ["Add more specific examples"],
            evaluated_by: "e2e-mock",
            evaluated_at: "2026-01-01T00:00:00Z",
          },
        }),
      });
    });

    // Fail the first save transiently, then let the same request reach the isolated API.
    let partSaveCalls = 0;
    await page.route("**/speaking/attempts/*/parts/*", async (route) => {
      if (route.request().method() !== "PUT") {
        await route.continue();
        return;
      }
      partSaveCalls += 1;
      if (partSaveCalls === 1) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Speaking save temporarily unavailable." }),
        });
        return;
      }
      await route.continue();
    });

    const transcriptTexts = [
      "I enjoy learning new skills because they help me solve problems. I practise English regularly to prepare for my studies abroad.",
      "I would like to learn photography because it combines creativity with technology. I would practise on weekends and learn from experienced photographers.",
      "Lifelong learning is important because technology and workplaces change quickly. Learning new skills helps people adapt and gives them more opportunities.",
    ];

    for (const partNumber of [1, 2, 3]) {
      await expect(page.getByRole("heading", { name: new RegExp("Part " + partNumber) })).toBeVisible({
        timeout: 15_000,
      });

      // Parts 1 and 2 have a preparation screen; skip the countdown using the UI control.
      const startSpeakingButton = page.getByRole("button", { name: "Start speaking now" });
      if (await startSpeakingButton.isVisible().catch(() => false)) {
        await startSpeakingButton.click();
      }

      const transcript = page.getByPlaceholder(
        "Your transcript will appear here. You can edit it if needed…",
      );
      await expect(transcript).toBeVisible({ timeout: 10_000 });
      await transcript.fill(transcriptTexts[partNumber - 1]);
      await expect(transcript).toHaveValue(transcriptTexts[partNumber - 1]);

      const continueButton = page.getByRole("button", {
        name: partNumber === 3 ? "Finish test" : "Save & continue",
      });

      if (partNumber === 1) {
        const failedSave = page.waitForResponse((response) =>
          response.request().method() === "PUT" &&
          /\/speaking\/attempts\/[^/]+\/parts\/[^/]+$/.test(response.url()) &&
          response.status() === 503,
        );
        await continueButton.click();
        await failedSave;
        await expect(page.locator(".floating-error")).toContainText(
          "Speaking save temporarily unavailable.",
          { timeout: 10_000 },
        );
        await expect(page.getByRole("heading", { name: "Part 1" })).toBeVisible();
        await expect(page.getByRole("heading", { name: "Part 2" })).toHaveCount(0);
        await expect(transcript).toHaveValue(transcriptTexts[0]);

        // Retry the same Part 1 save; this request reaches the isolated API.
        const retriedSave = page.waitForResponse((response) =>
          response.request().method() === "PUT" &&
          /\/speaking\/attempts\/[^/]+\/parts\/[^/]+$/.test(response.url()) &&
          response.status() === 200,
        );
        await continueButton.click();
        const saved = await retriedSave;
        expect((await saved.json()).transcript).toBe(transcriptTexts[0]);
      } else {
        const saveResponse = page.waitForResponse((response) =>
          response.request().method() === "PUT" &&
          /\/speaking\/attempts\/[^/]+\/parts\/[^/]+$/.test(response.url()) &&
          response.status() === 200,
        );
        await continueButton.click();
        const saved = await saveResponse;
        expect((await saved.json()).transcript).toBe(transcriptTexts[partNumber - 1]);
      }

      if (partNumber < 3) {
        await expect(page.getByRole("heading", { name: new RegExp("Part " + (partNumber + 1)) })).toBeVisible({
          timeout: 15_000,
        });
      }
    }

    await expect(page.getByRole("heading", { name: "Your Speaking review" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.locator(".result-card")).toHaveCount(3);
    await expect(page.locator(".result-card .score")).toHaveText(["7", "7", "7"]);
    await expect(page.getByText("Deterministic Speaking evaluation feedback.")).toHaveCount(3);
    await expect(page.getByText("Ideas are clearly organised").first()).toBeVisible();
    await expect(page.getByText("Add more specific examples").first()).toBeVisible();
    expect(evaluationCalls).toBe(3);

    // Open each saved transcript in the final review, proving all three parts persisted.
    for (let index = 0; index < transcriptTexts.length; index += 1) {
      const transcriptDetails = page.locator(".transcript-details").nth(index);
      await transcriptDetails.locator("summary").click();
      await expect(transcriptDetails).toContainText(transcriptTexts[index]);
    }
  });
});
