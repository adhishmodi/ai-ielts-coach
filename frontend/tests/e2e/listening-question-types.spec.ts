import { expect, test } from "@playwright/test";

test("Listening renders all seven supported question types with appropriate answer controls", async ({ page }) => {
  const questions = [
    { id: "q-mcq", question_text: "Which drink was ordered?", question_type: "multiple_choice", options: ["Tea", "Coffee"], order: 1 },
    { id: "q-match", question_text: "Match the person to the activity.", question_type: "matching", options: ["Ava", "Noah"], order: 2 },
    { id: "q-form", question_text: "Complete the booking form.", question_type: "form_completion", options: null, order: 3 },
    { id: "q-sentence", question_text: "Complete the sentence.", question_type: "sentence_completion", options: null, order: 4 },
    { id: "q-note", question_text: "Complete the notes.", question_type: "note_completion", options: null, order: 5 },
    { id: "q-short", question_text: "What time does it start?", question_type: "short_answer", options: null, order: 6 },
    { id: "q-map", question_text: "Select the location marked B.", question_type: "map_labeling", options: ["Library", "Station"], order: 7 },
  ];
  const practiceTest = {
    id: "listening-types-test",
    title: "Question Types Test",
    description: "Isolated renderer test",
    difficulty: "easy",
    time_limit_minutes: 40,
    sections: [{
      id: "section-1",
      title: "Question types",
      instructions: "Answer each question.",
      audio_url: null,
      order: 1,
      questions,
    }],
  };

  await page.route("**/api/v1/listening/tests", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([practiceTest]) });
  });
  await page.route("**/api/v1/listening/tests/*/start", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        attempt_id: "attempt-question-types",
        listening_test_id: practiceTest.id,
        started_at: new Date().toISOString(),
      }),
    });
  });

  await page.goto("/listening");
  const testCard = page.locator(".test-card").filter({ hasText: "Question Types Test" });
  await expect(testCard).toBeVisible();
  await testCard.getByRole("button", { name: "Practice mode" }).click();

  for (const type of [
    "multiple_choice",
    "matching",
    "form_completion",
    "sentence_completion",
    "note_completion",
    "short_answer",
    "map_labeling",
  ]) {
    await expect(page.locator(`[data-question-type="${type}"]`)).toBeVisible();
  }

  await page.getByLabel("Tea").check();
  await page.getByLabel("Answer for question 2").selectOption({ label: "Noah" });
  await page.getByLabel("Answer for question 3").fill("Adhish");
  await page.getByLabel("Answer for question 4").fill("at noon");
  await page.getByLabel("Answer for question 5").fill("Room 12");
  await page.getByLabel("Answer for question 6").fill("9:30");
  await page.getByLabel("Answer for question 7").selectOption({ label: "Station" });

  await expect(page.getByLabel("Tea")).toBeChecked();
  await expect(page.getByLabel("Answer for question 2")).toHaveValue("Noah");
  await expect(page.getByLabel("Answer for question 3")).toHaveValue("Adhish");
  await expect(page.getByLabel("Answer for question 4")).toHaveValue("at noon");
  await expect(page.getByLabel("Answer for question 5")).toHaveValue("Room 12");
  await expect(page.getByLabel("Answer for question 6")).toHaveValue("9:30");
  await expect(page.getByLabel("Answer for question 7")).toHaveValue("Station");
});
