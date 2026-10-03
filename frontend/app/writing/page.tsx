"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  apiFetch, clearTokens, WritingTest, WritingTask, AttemptStart, AttemptDetail,
  DraftResponse, SubmitResponse, EvaluateResponse, Evaluation
} from "../../lib/api";

type View = "select" | "test" | "results";

function formatTime(seconds: number) {
  const safe = Math.max(0, seconds);
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}

export default function WritingPage() {
  const router = useRouter();
  const [view, setView] = useState<View>("select");
  const [tests, setTests] = useState<WritingTest[]>([]);
  const [selectedTest, setSelectedTest] = useState<WritingTest | null>(null);
  const [attempt, setAttempt] = useState<AttemptStart | null>(null);
  const [attemptDetail, setAttemptDetail] = useState<AttemptDetail | null>(null);
  const [activeTask, setActiveTask] = useState(1);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [draftMeta, setDraftMeta] = useState<Record<string, DraftResponse>>({});
  const [evaluations, setEvaluations] = useState<Record<string, Evaluation>>({});
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState<SubmitResponse | null>(null);

  const active = useMemo(
    () => selectedTest?.tasks.find((task) => task.task_number === activeTask) ?? selectedTest?.tasks[0],
    [selectedTest, activeTask]
  );

  const wordCount = active ? (answers[active.id] ?? "").trim().split(/\s+/).filter(Boolean).length : 0;

  useEffect(() => {
    loadTests();
  }, []);

  useEffect(() => {
    if (view !== "test" || !attempt) return;
    const timer = window.setInterval(() => {
      const end = new Date(attempt.started_at).getTime() + (selectedTest?.time_limit_minutes ?? 60) * 60000;
      const remaining = Math.max(0, Math.ceil((end - Date.now()) / 1000));
      setSecondsLeft(remaining);
      if (remaining === 0) {
        window.clearInterval(timer);
        void submitTest(true);
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [view, attempt, selectedTest]);

  useEffect(() => {
    if (view !== "test" || !active || !attempt) return;
    const timer = window.setTimeout(() => void saveDraft(active, answers[active.id] ?? ""), 900);
    return () => window.clearTimeout(timer);
  }, [answers, active, attempt, view]);

  async function loadTests() {
    try {
      setError("");
      setTests(await apiFetch<WritingTest[]>("/writing/tests"));
    } catch (err) {
      if (String(err).includes("401")) {
        clearTokens();
        router.replace("/login");
      } else {
        setError(err instanceof Error ? err.message : "Could not load Writing tests.");
      }
    }
  }

  async function startTest(test: WritingTest) {
    setBusy(true);
    setError("");
    try {
      const started = await apiFetch<AttemptStart>(`/writing/tests/${test.id}/start`, { method: "POST" });
      setSelectedTest(test);
      setAttempt(started);
      setAnswers({});
      setDraftMeta({});
      setEvaluations({});
      setAttemptDetail(null);
      setSubmitted(null);
      setActiveTask(test.tasks[0]?.task_number ?? 1);
      setSecondsLeft(test.time_limit_minutes * 60);
      setView("test");
      setMessage("Test started. Your answers autosave as you type.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start test.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraft(task: WritingTask, text: string) {
    if (!attempt) return;
    setSaving(true);
    try {
      const saved = await apiFetch<DraftResponse>(`/writing/attempts/${attempt.attempt_id}/tasks/${task.id}`, {
        method: "PUT",
        body: JSON.stringify({ response_text: text }),
      });
      setDraftMeta((current) => ({ ...current, [task.id]: saved }));
      setLastSaved(new Date());
      setMessage("Saved");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Autosave failed");
    } finally {
      setSaving(false);
    }
  }

  async function submitTest(auto = false) {
    if (!attempt || !selectedTest || busy) return;
    setBusy(true);
    setError("");
    try {
      for (const task of selectedTest.tasks) {
        await saveDraft(task, answers[task.id] ?? "");
      }
      const result = await apiFetch<SubmitResponse>(`/writing/attempts/${attempt.attempt_id}/submit`, { method: "POST" });
      setSubmitted(result);
      const detail = await apiFetch<AttemptDetail>(`/writing/attempts/${attempt.attempt_id}`);
      setAttemptDetail(detail);
      setView("results");
      setMessage(auto ? "Time is up. Your test was submitted." : "Test submitted.");
      if (detail.submissions.length) {
        for (const submission of detail.submissions) {
          try {
            const evaluated = await apiFetch<EvaluateResponse>(`/writing/submissions/${submission.id}/evaluate`, { method: "POST" });
            setEvaluations((current) => ({ ...current, [submission.task_id]: evaluated.evaluation }));
          } catch (err) {
            setError(err instanceof Error ? err.message : "AI evaluation failed.");
          }
        }
      }
      const refreshed = await apiFetch<AttemptDetail>(`/writing/attempts/${attempt.attempt_id}`);
      setAttemptDetail(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit the test.");
    } finally {
      setBusy(false);
    }
  }

  function answer(task: WritingTask) {
    return answers[task.id] ?? "";
  }

  function evaluationFor(task: WritingTask) {
    return evaluations[task.id] ?? attemptDetail?.submissions.find((s) => s.task_id === task.id)?.evaluation ?? null;
  }

  if (view === "select") {
    return (
      <main className="app-shell">
        <header className="topbar"><div><div className="brand">AI IELTS Coach</div><span className="muted">Writing</span></div><div className="top-actions"><button className="ghost-button" onClick={() => router.push("/speaking")}>Speaking</button><button className="ghost-button" onClick={() => { clearTokens(); router.replace("/login"); }}>Sign out</button></div></header>
        <section className="hero"><div className="eyebrow">WRITING PRACTICE</div><h1>Build your Writing score.</h1><p>Choose a test, write both tasks under exam conditions, and receive AI feedback after submission.</p></section>
        {error && <div className="error-box page-message">{error}</div>}
        <section className="test-grid">
          {tests.map((test) => (
            <article className="test-card" key={test.id}>
              <div className="pill-row"><span className="pill">{test.test_type}</span><span className="pill">{test.difficulty}</span></div>
              <h2>{test.title}</h2>
              <p className="muted">{test.description || "IELTS Writing practice test."}</p>
              <div className="test-meta"><span>{test.tasks.length} tasks</span><span>{test.time_limit_minutes} min</span></div>
              <button className="primary-button" disabled={busy} onClick={() => startTest(test)}>{busy ? "Starting…" : "Start test"}</button>
            </article>
          ))}
          {!tests.length && !error && <div className="empty-card">Loading available Writing tests…</div>}
        </section>
      </main>
    );
  }

  if (view === "results" && selectedTest && attemptDetail) {
    return (
      <main className="app-shell">
        <header className="topbar"><div><div className="brand">AI IELTS Coach</div><span className="muted">Writing results</span></div><div className="top-actions"><button className="ghost-button" onClick={() => router.push("/speaking")}>Speaking</button><button className="ghost-button" onClick={() => setView("select")}>Back to tests</button></div></header>
        <section className="result-hero">
          <div><div className="eyebrow">TEST COMPLETE</div><h1>Your Writing review</h1><p className="muted">{submitted?.below_minimum_tasks.length ? `Task ${submitted.below_minimum_tasks.join(" and ")} fell below the recommended word count.` : "Both tasks were submitted successfully."}</p></div>
          <div className="overall-band"><span>Overall</span><strong>{attemptDetail.overall_band ?? "—"}</strong></div>
        </section>
        <div className="results-grid">
          {selectedTest.tasks.map((task) => {
            const evaluation = evaluationFor(task);
            const submission = attemptDetail.submissions.find((s) => s.task_id === task.id);
            return <article className="result-card" key={task.id}>
              <div className="result-card-head"><div><span className="eyebrow">TASK {task.task_number}</span><h2>{task.task_type === "essay" ? "Essay" : "Report"}</h2></div><strong className="score">{evaluation?.overall_band ?? "—"}</strong></div>
              <div className="score-grid">
                <Score label={task.task_number === 2 ? "Task Response" : "Task Achievement"} value={task.task_number === 2 ? evaluation?.task_response_band : evaluation?.task_achievement_band} />
                <Score label="Coherence" value={evaluation?.coherence_band} />
                <Score label="Lexical" value={evaluation?.lexical_band} />
                <Score label="Grammar" value={evaluation?.grammar_band} />
              </div>
              {evaluation ? <>
                <div className="feedback"><h3>AI feedback</h3><p>{evaluation.feedback || "No summary provided."}</p></div>
                <div className="feedback-columns"><div><h3>Strengths</h3><ul>{(evaluation.strengths ?? []).map((item, i) => <li key={i}>{item}</li>)}</ul></div><div><h3>Improve next</h3><ul>{(evaluation.improvements ?? []).map((item, i) => <li key={i}>{item}</li>)}</ul></div></div>
              </> : <div className="pending-box">AI evaluation is unavailable. {submission ? "The submission is saved." : ""}</div>}
            </article>;
          })}
        </div>
      </main>
    );
  }

  return (
    <main className="app-shell test-shell">
      <header className="topbar">
        <div><div className="brand">AI IELTS Coach</div><span className="muted">{selectedTest?.title}</span></div>
        <div className="top-actions"><button className="ghost-button" onClick={() => router.push("/speaking")}>Speaking</button><div className={secondsLeft <= 300 ? "timer danger" : "timer"}>{formatTime(secondsLeft)}</div></div>
      </header>
      <div className="test-layout">
        <aside className="task-sidebar">
          <div className="sidebar-label">Tasks</div>
          {selectedTest?.tasks.map((task) => {
            const count = (answers[task.id] ?? "").trim().split(/\s+/).filter(Boolean).length;
            return <button key={task.id} className={task.task_number === activeTask ? "task-tab active" : "task-tab"} onClick={() => setActiveTask(task.task_number)}>
              <span>Task {task.task_number}</span><small>{count} words</small>
            </button>;
          })}
          <div className="save-status">{saving ? "Saving…" : lastSaved ? `Saved ${lastSaved.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Autosave enabled"}</div>
          <button className="submit-button" disabled={busy} onClick={() => void submitTest(false)}>{busy ? "Submitting…" : "Submit test"}</button>
        </aside>
        <section className="editor-panel">
          {active && <>
            <div className="task-header"><div><span className="eyebrow">TASK {active.task_number}</span><h1>{active.task_type === "essay" ? "Write an essay" : "Write a report"}</h1></div><div className="word-target">Minimum {active.minimum_words} words</div></div>
            <div className="prompt-card"><strong>{active.prompt}</strong>{active.instructions && <p>{active.instructions}</p>}</div>
            <textarea autoFocus value={answer(active)} onChange={(e) => setAnswers((current) => ({ ...current, [active.id]: e.target.value }))} placeholder="Start writing here…" />
            <div className={wordCount < active.minimum_words ? "word-count below" : "word-count"}><span>{wordCount} words</span><span>{wordCount < active.minimum_words ? `${active.minimum_words - wordCount} more recommended` : "Minimum reached"}</span></div>
          </>}
        </section>
      </div>
      {error && <div className="floating-error">{error}</div>}
      {message && <div className="floating-message">{message}</div>}
    </main>
  );
}

function Score({ label, value }: { label: string; value?: number | null }) {
  return <div className="score-item"><span>{label}</span><strong>{value ?? "—"}</strong></div>;
}