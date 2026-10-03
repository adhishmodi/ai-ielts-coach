"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  apiFetch, clearTokens, ReadingTest, ReadingAttemptStart, ReadingAttemptDetail,
  ReadingSubmissionResponse
} from "../../lib/api";

type View = "select" | "test" | "results";

function formatTime(seconds: number) {
  const safe = Math.max(0, seconds);
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}

function isChoice(question: { question_type: string; options?: unknown[] | null }) {
  return Array.isArray(question.options) && question.options.length > 0;
}

function displayType(type: string) {
  return type.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ReadingPage() {
  const router = useRouter();
  const [view, setView] = useState<View>("select");
  const [tests, setTests] = useState<ReadingTest[]>([]);
  const [selectedTest, setSelectedTest] = useState<ReadingTest | null>(null);
  const [attempt, setAttempt] = useState<ReadingAttemptStart | null>(null);
  const [result, setResult] = useState<ReadingSubmissionResponse | null>(null);
  const [detail, setDetail] = useState<ReadingAttemptDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [activePassage, setActivePassage] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const passage = selectedTest?.passages[activePassage] ?? null;
  const allQuestions = useMemo(
    () => selectedTest?.passages.flatMap((p) => p.questions) ?? [],
    [selectedTest]
  );
  const answered = allQuestions.filter((q) => (answers[q.id] ?? "").trim()).length;

  useEffect(() => { void loadTests(); }, []);

  useEffect(() => {
    if (view !== "test" || !attempt || !selectedTest) return;
    const timer = window.setInterval(() => {
      const end = new Date(attempt.started_at).getTime() + selectedTest.time_limit_minutes * 60000;
      const remaining = Math.max(0, Math.ceil((end - Date.now()) / 1000));
      setSecondsLeft(remaining);
      if (remaining === 0) {
        window.clearInterval(timer);
        void submitTest(true);
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [view, attempt, selectedTest]);

  async function loadTests() {
    try {
      setError("");
      setTests(await apiFetch<ReadingTest[]>("/reading/tests"));
    } catch (err) {
      if (String(err).includes("401")) { clearTokens(); router.replace("/login"); }
      else setError(err instanceof Error ? err.message : "Could not load Reading tests.");
    }
  }

  async function startTest(test: ReadingTest) {
    setBusy(true); setError("");
    try {
      const started = await apiFetch<ReadingAttemptStart>(`/reading/tests/${test.id}/start`, { method: "POST" });
      setSelectedTest(test); setAttempt(started); setResult(null); setDetail(null);
      setAnswers({}); setActivePassage(0); setSecondsLeft(test.time_limit_minutes * 60); setView("test");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start test.");
    } finally { setBusy(false); }
  }

  async function submitTest(auto = false) {
    if (!attempt || busy) return;
    setBusy(true); setError("");
    try {
      const payload = { answers: Object.entries(answers).map(([question_id, answer]) => ({ question_id, answer })) };
      const submitted = await apiFetch<ReadingSubmissionResponse>(`/reading/attempts/${attempt.attempt_id}/submit`, {
        method: "POST", body: JSON.stringify(payload)
      });
      const attemptDetail = await apiFetch<ReadingAttemptDetail>(`/reading/attempts/${attempt.attempt_id}`);
      setResult(submitted); setDetail(attemptDetail); setView("results");
      if (auto) setError("Time is up. Your Reading test was submitted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit the test.");
    } finally { setBusy(false); }
  }

  if (view === "select") return (
    <main className="app-shell">
      <header className="topbar"><div><div className="brand">AI IELTS Coach</div><span className="muted">Reading</span></div><div className="top-actions"><button className="ghost-button" onClick={() => router.push("/")}>Dashboard</button><button className="ghost-button" onClick={() => { clearTokens(); router.replace("/login"); }}>Sign out</button></div></header>
      <section className="hero"><div className="eyebrow">READING PRACTICE</div><h1>Read smarter under time pressure.</h1><p>Work through passages and IELTS-style question types, submit once, then review every answer and explanation available from the test.</p></section>
      {error && <div className="error-box page-message">{error}</div>}
      <section className="test-grid">
        {tests.map((test) => <article className="test-card" key={test.id}>
          <div className="pill-row"><span className="pill">{test.difficulty}</span><span className="pill">Academic</span></div>
          <h2>{test.title}</h2><p className="muted">{test.description || "IELTS Reading practice test."}</p>
          <div className="test-meta"><span>{test.passages.length} passages</span><span>{test.passages.reduce((n, p) => n + p.questions.length, 0)} questions</span><span>{test.time_limit_minutes} min</span></div>
          <button className="primary-button" disabled={busy} onClick={() => startTest(test)}>{busy ? "Starting…" : "Start test"}</button>
        </article>)}
        {!tests.length && !error && <div className="empty-card">Loading available Reading tests…</div>}
      </section>
    </main>
  );

  if (view === "results" && selectedTest && detail && result) return (
    <main className="app-shell">
      <header className="topbar"><div><div className="brand">AI IELTS Coach</div><span className="muted">Reading results</span></div><div className="top-actions"><button className="ghost-button" onClick={() => router.push("/")}>Dashboard</button><button className="ghost-button" onClick={() => setView("select")}>Back to tests</button></div></header>
      <section className="result-hero"><div><div className="eyebrow">TEST COMPLETE</div><h1>Your Reading review</h1><p className="muted">Review your score and each submitted answer.</p></div><div className="overall-band"><span>Band</span><strong>{result.band_score}</strong><small>{result.score}/{result.total_questions} correct</small></div></section>
      <section className="review-list">
        {selectedTest.passages.map((p) => <article className="result-card" key={p.id}>
          <div className="review-passage-title"><span className="eyebrow">PASSAGE {p.order + 1}</span><h2>{p.title}</h2></div>
          {p.questions.map((q, i) => {
            const answer = detail.answers.find((a) => a.question_id === q.id);
            return <div className="review-question" key={q.id}>
              <div><strong>Question {i + 1}</strong><span className="question-type">{displayType(q.question_type)}</span></div>
              <p>{q.question_text}</p>
              <div className={answer?.is_correct ? "answer-row correct" : "answer-row incorrect"}><span>Your answer</span><strong>{answer?.user_answer || "Not answered"}</strong></div>
              {!answer?.is_correct && <div className="answer-row"><span>Correct answer</span><strong>{answer?.correct_answer ?? "—"}</strong></div>}
            </div>;
          })}
        </article>)}
      </section>
    </main>
  );

  return (
    <main className="app-shell test-shell">
      <header className="topbar">
        <div><div className="brand">AI IELTS Coach</div><span className="muted">{selectedTest?.title}</span></div>
        <div className="top-actions"><button className="ghost-button" onClick={() => router.push("/")}>Dashboard</button><div className={secondsLeft <= 300 ? "timer danger" : "timer"}>{formatTime(secondsLeft)}</div></div>
      </header>
      <div className="skill-test-layout">
        <aside className="passage-sidebar">
          <div className="sidebar-label">Passages</div>
          {selectedTest?.passages.map((p, i) => <button key={p.id} className={i === activePassage ? "task-tab active" : "task-tab"} onClick={() => setActivePassage(i)}>
            <span>Passage {p.order + 1}</span><small>{p.questions.length} questions</small>
          </button>)}
          <div className="progress-box"><strong>{answered}/{allQuestions.length}</strong><span>answered</span></div>
          <button className="submit-button" disabled={busy} onClick={() => void submitTest(false)}>{busy ? "Submitting…" : "Submit test"}</button>
        </aside>
        <section className="reading-workspace">
          {passage && <><div className="skill-workspace-head"><div><span className="eyebrow">PASSAGE {passage.order + 1}</span><h1>{passage.title}</h1></div><span>{passage.questions.length} questions</span></div>
            <div className="reading-columns">
              <article className="passage-text">{passage.content}</article>
              <div className="question-list">{passage.questions.map((q, i) => <Question key={q.id} number={i + 1} question={q} value={answers[q.id] ?? ""} onChange={(value) => setAnswers((current) => ({ ...current, [q.id]: value }))} />)}</div>
            </div>
          </>}
        </section>
      </div>
      {error && <div className="floating-error">{error}</div>}
    </main>
  );
}

function Question({ number, question, value, onChange }: {
  number: number;
  question: ReadingTest["passages"][number]["questions"][number];
  value: string;
  onChange: (value: string) => void;
}) {
  const options = Array.isArray(question.options) ? question.options : [];
  return <article className="question-card">
    <div className="question-card-head"><strong>Question {number}</strong><span className="question-type">{displayType(question.question_type)}</span></div>
    <p>{question.question_text}</p>
    {isChoice(question) ? <div className="option-list">{options.map((option, i) => {
      const text = String(option);
      return <label className={value === text ? "option selected" : "option"} key={i}><input type="radio" name={question.id} value={text} checked={value === text} onChange={(e) => onChange(e.target.value)} /><span>{text}</span></label>;
    })}</div> : <input className="answer-input" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Type your answer" />}
  </article>;
}
