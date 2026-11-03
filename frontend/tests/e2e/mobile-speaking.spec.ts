import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `mobile-speaking-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

async function expectNoHorizontalOverflow(page: Page) {
  for (const width of [390, 768, 1280]) {
    await page.setViewportSize({ width, height: 844 });
    const dimensions = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
    }));
    expect(
      dimensions.documentWidth,
      `No horizontal overflow at ${width}px viewport`,
    ).toBeLessThanOrEqual(dimensions.viewportWidth);
  }
  // Keep the existing mobile journey and its following assertions at 390px.
  await page.setViewportSize({ width: 390, height: 844 });
}

test.describe("responsive Speaking journey (isolated CI database only)", () => {
  test.skip(
    Boolean(process.env.PLAYWRIGHT_BASE_URL),
    "This journey creates an account and speaking attempt; run only against the isolated PostgreSQL service in CI.",
  );

  test("learner completes all three parts and reviews saved transcripts at 390px", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/register");
    await page.getByLabel("Full name").fill("Mobile Speaking Learner");
    await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
    await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });

    // Make the workflow deterministic and independent of a physical microphone.
    await page.addInitScript(() => {
      if (navigator.mediaDevices?.getUserMedia) {
        Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
          configurable: true,
          value: async () => {
            throw new Error("Microphone intentionally unavailable in this mobile E2E test.");
          },
        });
      }
    });

    await page.goto("/speaking");
    const testCard = page.locator(".test-card").filter({
      has: page.getByRole("heading", { name: "E2E Speaking Test", exact: true }),
    });
    await expect(testCard).toBeVisible({ timeout: 15_000 });
    await expectNoHorizontalOverflow(page);
    await expect(testCard.getByRole("button", { name: "Start speaking test" })).toBeVisible();
    await testCard.getByRole("button", { name: "Start speaking test" }).click();

    // Mock only evaluation. Attempt creation, response saves, submission, and
    // persisted attempt reads continue through the isolated CI API/database.
    let evaluationCalls = 0;
    await page.route("**/speaking/responses/*/evaluate", async (route) => {
      evaluationCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          response_id: `mobile-speaking-response-${evaluationCalls}`,
          status: "evaluated",
          evaluation: {
            id: `mobile-speaking-evaluation-${evaluationCalls}`,
            response_id: `mobile-speaking-response-${evaluationCalls}`,
            fluency_band: 7,
            lexical_band: 7,
            grammar_band: 6.5,
            pronunciation_band: 6.5,
            overall_band: 7,
            feedback: "Mobile Speaking deterministic feedback.",
            strengths: ["Ideas are clearly organised"],
            improvements: ["Add specific examples"],
            evaluated_by: "e2e-mock",
            evaluated_at: "2026-01-01T00:00:00Z",
          },
        }),
      });
    });

    const transcripts = [
      "I enjoy learning new skills because they help me solve problems. I practise English regularly to prepare for my studies abroad.",
      "I would like to learn photography because it combines creativity with technology. I would practise on weekends and learn from experienced photographers.",
      "Lifelong learning is important because technology and workplaces change quickly. Learning new skills helps people adapt and gives them more opportunities.",
    ];

    for (const partNumber of [1, 2, 3]) {
      await expect(page.getByRole("heading", { name: new RegExp(`Part ${partNumber}`) })).toBeVisible({
        timeout: 15_000,
      });
      await expectNoHorizontalOverflow(page);

      // Parts 1 and 2 expose a UI action to skip the preparation countdown.
      const startSpeaking = page.getByRole("button", { name: "Start speaking now" });
      if (await startSpeaking.isVisible().catch(() => false)) {
        await startSpeaking.click();
      }

      const transcript = page.getByPlaceholder(
        "Your transcript will appear here. You can edit it if needed…",
      );
      await expect(transcript).toBeVisible({ timeout: 10_000 });
      await transcript.fill(transcripts[partNumber - 1]);
      await expect(transcript).toHaveValue(transcripts[partNumber - 1]);

      const nextButton = page.getByRole("button", {
        name: partNumber === 3 ? "Finish test" : "Save & continue",
      });
      const savedResponse = page.waitForResponse((response) =>
        response.request().method() === "PUT" &&
        /\/speaking\/attempts\/[^/]+\/parts\/[^/]+$/.test(response.url()) &&
        response.status() === 200,
      );
      await nextButton.click();
      const saved = await savedResponse;
      expect((await saved.json()).transcript).toBe(transcripts[partNumber - 1]);

      if (partNumber < 3) {
        await expect(page.getByRole("heading", { name: new RegExp(`Part ${partNumber + 1}`) })).toBeVisible({
          timeout: 15_000,
        });
      }
    }

    await expect(page.getByRole("heading", { name: "Your Speaking review" })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.locator(".result-card")).toHaveCount(3);
    await expect(page.locator(".result-card .score")).toHaveText(["7", "7", "7"]);
    await expect(page.getByText("Mobile Speaking deterministic feedback.")).toHaveCount(3);
    expect(evaluationCalls).toBe(3);
    await expectNoHorizontalOverflow(page);

    for (let index = 0; index < transcripts.length; index += 1) {
      const details = page.locator(".transcript-details").nth(index);
      await details.locator("summary").click();
      await expect(details).toContainText(transcripts[index]);
    }
  });
});
