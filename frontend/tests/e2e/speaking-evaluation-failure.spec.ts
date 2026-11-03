import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `speaking-evaluation-failure-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function registerLearner(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Speaking Evaluation Failure Learner");
  await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
}

test.describe("Speaking evaluation failure (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "This journey creates an account and speaking attempt; run only against isolated CI PostgreSQL.",
  );

  test("preserves submitted transcripts after evaluation failure and permits an authenticated retry", async ({ page }) => {
    await registerLearner(page);

    // Avoid physical microphone and speech-recognition dependencies.
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
    const testCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Speaking Test", exact: true }),
    });
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await testCard.getByRole("button", { name: "Start speaking test" }).click();

    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
    const startResponse = page.waitForResponse((response) =>
      response.request().method() === "POST" &&
      /\/speaking\/tests\/[^/]+\/start$/.test(response.url()) &&
      response.status() === 200,
    );

    let evaluationCalls = 0;
    await page.route("**/speaking/responses/*/evaluate", async (route) => {
      evaluationCalls += 1;
      if (evaluationCalls <= 3) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Speaking evaluation temporarily unavailable." }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          response_id: "e2e-speaking-retry-response",
          status: "evaluated",
          evaluation: {
            id: "e2e-speaking-retry-evaluation",
            response_id: "e2e-speaking-retry-response",
            fluency_band: 7,
            lexical_band: 7,
            grammar_band: 6.5,
            pronunciation_band: 6.5,
            overall_band: 7,
            feedback: "Speaking evaluation recovered after retry.",
            strengths: ["Ideas are clearly organised"],
            improvements: ["Add specific examples"],
            evaluated_by: "e2e-mock",
            evaluated_at: "2026-01-01T00:00:00Z",
          },
        }),
      });
    });

    const started = await startResponse;
    const attemptId = (await started.json()).attempt_id;
    const transcripts = [
      "I enjoy learning new skills because they help me solve problems. I practise English regularly to prepare for my studies abroad.",
      "I would like to learn photography because it combines creativity with technology. I would practise on weekends and learn from experienced photographers.",
      "Lifelong learning is important because technology and workplaces change quickly. Learning new skills helps people adapt and gives them more opportunities.",
    ];

    for (const partNumber of [1, 2, 3]) {
      await expect(page.getByRole("heading", { name: new RegExp(`Part ${partNumber}`) })).toBeVisible({
        timeout: 15_000,
      });
      const startSpeaking = page.getByRole("button", { name: "Start speaking now" });
      if (await startSpeaking.isVisible().catch(() => false)) {
        await startSpeaking.click();
      }

      const transcript = page.getByPlaceholder(
        "Your transcript will appear here. You can edit it if needed…",
      );
      await expect(transcript).toBeVisible({ timeout: 10_000 });
      await transcript.fill(transcripts[partNumber - 1]);

      const saveResponse = page.waitForResponse((response) =>
        response.request().method() === "PUT" &&
        /\/speaking\/attempts\/[^/]+\/parts\/[^/]+$/.test(response.url()) &&
        response.status() === 200,
      );
      await page.getByRole("button", {
        name: partNumber === 3 ? "Finish test" : "Save & continue",
      }).click();
      const saved = await saveResponse;
      expect((await saved.json()).transcript).toBe(transcripts[partNumber - 1]);
    }

    await expect(page.getByRole("heading", { name: "Your Speaking review" })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByText("Speaking evaluation temporarily unavailable.").first()).toBeVisible();
    await expect(page.locator(".pending-box")).toHaveCount(3);
    await expect(page.locator(".overall-band strong")).toHaveText("—");
    await expect(page.locator(".result-card .score")).toHaveText(["—", "—", "—"]);
    expect(evaluationCalls).toBe(3);

    const accessToken = await page.evaluate(() => localStorage.getItem("access_token"));
    expect(accessToken).toBeTruthy();
    const detailResponse = await page.evaluate(async ({ apiBase, attemptId, accessToken }) => {
      const response = await fetch(`${apiBase}/speaking/attempts/${attemptId}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      return { status: response.status, body: await response.json() };
    }, { apiBase, attemptId, accessToken });
    expect(detailResponse.status).toBe(200);
    expect(detailResponse.body.responses.map((response: { transcript: string }) => response.transcript))
      .toEqual(transcripts);
    expect(detailResponse.body.responses.every((response: { evaluation?: unknown }) => !response.evaluation))
      .toBe(true);

    // The product currently has no retry button on the review screen. Exercise the
    // authenticated retry endpoint from the browser context without changing app UI.
    const responseId = detailResponse.body.responses[0].id;
    const retryResult = await page.evaluate(async ({ apiBase, responseId, accessToken }) => {
      const response = await fetch(`${apiBase}/speaking/responses/${responseId}/evaluate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
      });
      return { status: response.status, body: await response.json() };
    }, { apiBase, responseId, accessToken });
    expect(retryResult.status).toBe(200);
    expect(retryResult.body.evaluation.feedback).toBe("Speaking evaluation recovered after retry.");
    expect(evaluationCalls).toBe(4);

    // Retry does not alter or discard the persisted transcript.
    const afterRetry = await page.evaluate(async ({ apiBase, attemptId, accessToken }) => {
      const response = await fetch(`${apiBase}/speaking/attempts/${attemptId}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      return response.json();
    }, { apiBase, attemptId, accessToken });
    expect(afterRetry.responses[0].transcript).toBe(transcripts[0]);
    expect(afterRetry.responses[0].evaluation.feedback).toBe("Speaking evaluation recovered after retry.");
  });
});
