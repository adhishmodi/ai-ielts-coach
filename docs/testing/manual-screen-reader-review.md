# Manual Screen-Reader Review Checklist

This checklist supplements automated axe and keyboard tests. It is a **manual review protocol**, not evidence that the review has already been performed. Record the assistive technology, browser, build/commit, date, tester, and findings before marking any item complete.

## Test setup

- [ ] Use a dedicated test learner account and seeded practice content; do not use real learner data.
- [ ] Record app URL, commit/build, OS, browser/version, screen reader/version, and tester.
- [ ] Primary desktop pass: Windows + NVDA with Firefox (repeat critical flows in Chrome if available).
- [ ] Secondary pass: macOS + VoiceOver with Safari, or iOS + VoiceOver with Safari for touch-screen reading/navigation.
- [ ] Start with screen reader speech and browser zoom at the tester's normal settings; optionally repeat at 200% zoom.
- [ ] Use a fresh test account or resettable seeded state for state-mutating practice flows.

## Global navigation and orientation

- [ ] On login and registration, confirm the page title and main heading are announced and meaningful.
- [ ] Navigate by landmarks (banner, navigation, main, footer where present); verify landmarks are named and not confusingly duplicated.
- [ ] Navigate by headings; confirm levels and order provide a useful outline without skipped or misleading headings.
- [ ] Navigate by links and buttons; confirm names describe the destination/action and repeated names can be distinguished in context.
- [ ] Confirm keyboard focus is visible and screen-reader focus follows the visual focus order.
- [ ] Confirm route changes announce or expose the new page title/main heading; browser Back returns to an understandable location.
- [ ] Check that decorative icons and images do not add noisy or redundant announcements.

## Authentication

- [ ] On login and registration, each input announces its label, role, and required/invalid state where applicable.
- [ ] Password visibility controls (if present) announce their state and purpose.
- [ ] Submit the form empty and with invalid data; confirm errors are associated with the relevant fields and discoverable without searching the page.
- [ ] Submit valid test credentials; confirm success/navigation is announced and the dashboard is understandable.

## Dashboard and skill navigation

- [ ] Confirm the dashboard heading and practice-area grouping are announced.
- [ ] Navigate all four skill cards (Reading, Listening, Writing, Speaking) using screen-reader link/button navigation.
- [ ] Confirm each card's accessible name communicates the skill and action without requiring visual context.
- [ ] Confirm loading, empty, and error states are announced when encountered.

## Reading

- [ ] Start a seeded Reading attempt; confirm the test title, passage, question grouping, and progress are announced in a sensible order.
- [ ] For each question type present in the seeded test, confirm prompt and answer controls have useful labels and grouping.
- [ ] Confirm radio/checkbox choices announce label and selected state; text inputs announce question context.
- [ ] Move between questions/passages (where supported); confirm the new context and progress are discoverable.
- [ ] Submit; confirm validation or submission progress/status is announced.
- [ ] In review, confirm score/band and question-by-question correct answer, learner answer, and feedback are navigable and understandable.

## Listening

- [ ] Start a practice attempt; confirm section heading, instructions, and audio player controls are announced.
- [ ] Operate audio controls by keyboard and screen reader; confirm play/pause and relevant state are exposed.
- [ ] Confirm question controls are associated with their prompts and answer labels.
- [ ] Navigate sections; confirm the active section and changed question content are announced.
- [ ] Check timer/recording-lock or exam-mode instructions, if shown, are announced without excessively interrupting speech.
- [ ] Submit and review; confirm submission status, score, answers, and feedback are accessible.

## Writing

- [ ] Start a Writing attempt; confirm task number, prompt, word target, and editor label are announced.
- [ ] Enter text; confirm word count and autosave status changes are announced appropriately (not on every keystroke).
- [ ] Switch between Task 1 and Task 2; confirm the selected task and its prompt/editor context are clear.
- [ ] Submit; confirm progress/status and any validation errors are announced.
- [ ] Review each task's response, evaluation status, band/score, feedback, strengths, and improvement suggestions in a logical reading order.
- [ ] Do not treat draft resume after reload as supported; that feature is currently unavailable.

## Speaking

- [ ] Start a Speaking attempt; confirm part number, prompt, preparation instructions, and available actions are announced.
- [ ] If recording controls appear, verify names, state, and instructions; do not assume microphone capture is accessible merely because transcript editing is.
- [ ] Start/stop or transition from preparation using keyboard; confirm status changes are announced.
- [ ] Confirm transcript editor has a useful label and its content is readable/editable.
- [ ] Save and advance through Parts 1–3; confirm save/progress and part changes are announced.
- [ ] Submit and review; confirm transcript, evaluation status, scores, feedback, strengths, and improvements are navigable.
- [ ] If evaluation fails, confirm the unavailable/error state is announced and saved transcript remains accessible.

## Cross-flow status, errors, and recovery

- [ ] Trigger a recoverable save or submission failure in a test environment; confirm the error is announced and the user can locate the retry action.
- [ ] Confirm successful save/submission feedback is announced once and does not steal focus unexpectedly.
- [ ] Confirm focus remains sensible after validation errors, loading states, and route changes.
- [ ] Check that status messages use appropriate live-region behavior and do not repeatedly interrupt screen-reader speech.
- [ ] Confirm no keyboard trap occurs in any tested flow.

## Findings log

For each issue, record:
- Screen/route and exact steps to reproduce
- Expected announcement or navigation behavior
- Actual announcement/behavior
- OS, browser, screen reader, versions, and commit/build
- Severity and impact on task completion
- Screenshot/video or screen-reader speech log when appropriate
- Suggested remediation and retest result

| ID | Route/flow | AT + browser | Finding / expected vs actual | Severity | Status |
|---|---|---|---|---|---|
| | | | | | |

## Exit criteria

- [ ] Complete the global checks and at least one full flow for each skill.
- [ ] Record all findings, including “no issue observed” for reviewed areas.
- [ ] Re-test fixes with the same AT/browser combination.
- [ ] Keep automated axe and keyboard results separate from manual screen-reader results.
- [ ] Do not claim WCAG conformance based on this checklist alone.
