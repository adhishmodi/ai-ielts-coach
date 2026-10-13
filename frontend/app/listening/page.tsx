"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  apiFetch, clearTokens, ListeningTest, ListeningAttemptStart, ListeningAttemptDetail,
  ListeningSubmissionResponse
} from "../../lib/api";

type View = "select" | "test" | "results";

function formatTime(seconds: number) {
  const safe = Math.max(0, seconds);
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}

function displayType(type: string) {
  return type.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ListeningPage() {
  const router = useRouter();
  const [view, setView] = useState<View>("select");
  const [mode, setMode] = useState<"practice" | "exam">("practice");
  const [audioPlayedSections, setAudioPlayedSections] = useState<Record<string, boolean>>({});
  const [audioEndedSections, setAudioEndedSections] = useState<Record<string, boolean>>({});
  const [audioPlaying, setAudioPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const submitLock = useRef(false);
  const [tests, setTests] = useState<ListeningTest[]>([]);
  const [selectedTest, setSelectedTest] = useState<ListeningTest | null>(null);
  const [attempt, setAttempt] = useState<ListeningAttemptStart | null>(null);
  const [result, setResult] = useState<ListeningSubmissionResponse | null>(null);
  const [detail, setDetail] = useState<ListeningAttemptDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [activeSection, setActiveSection] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const sections = selectedTest?.sections ?? [];
  const allQuestions = useMemo(() => sections.flatMap((s) => s.questions), [sections]);
  const answered = allQuestions.filter((q) => (answers[q.id] ?? "").trim()).length;

  useEffect(() => { void loadTests(); }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    setAudioPlaying(false);
  }, [activeSection, view]);

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
      setError(""); setTests(await apiFetch<ListeningTest[]>("/listening/tests"));
    } catch (err) {
      if (String(err).includes("401")) { clearTokens(); router.replace("/login"); }
      else setError(err instanceof Error ? err.message : "Could not load Listening tests.");
    }
  }

  async function startTest(test: ListeningTest, selectedMode: "practice" | "exam") {
    setBusy(true); setError("");
    try {
      const started = await apiFetch<ListeningAttemptStart>(`/listening/tests/${test.id}/start`, { method: "POST" });
      setSelectedTest(test); setAttempt(started); setResult(null); setDetail(null);
      setMode(selectedMode); setAudioPlayedSections({}); setAudioEndedSections({}); setAudioPlaying(false);
      setAnswers({}); setActiveSection(0); setSecondsLeft(test.time_limit_minutes * 60); submitLock.current = false; setView("test");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start test.");
    } finally { setBusy(false); }
  }

  async function submitTest(auto = false) {
    if (!attempt || busy || submitLock.current) return;
    submitLock.current = true;
    setBusy(true); setError("");
    try {
      const payload = { answers: allQuestions.map((question) => ({ question_id: question.id, answer: answers[question.id] ?? "" })) };
      const submitted = await apiFetch<ListeningSubmissionResponse>(`/listening/attempts/${attempt.attempt_id}/submit`, { method: "POST", body: JSON.stringify(payload) });
      const attemptDetail = await apiFetch<ListeningAttemptDetail>(`/listening/attempts/${attempt.attempt_id}`);
      setResult(submitted); setDetail(attemptDetail); setView("results");
      if (auto) setError("Time is up. Your Listening test was submitted.");
    } catch (err) {
      submitLock.current = false;
      setError(err instanceof Error ? err.message : "Could not submit the test.");
    } finally { setBusy(false); }
  }

  if (view === "select") return (
    <main className="app-shell">
      <header className="topbar"><div><div className="brand">AI IELTS Coach</div><span className="muted">Listening</span></div><div className="top-actions"><button className="ghost-button" onClick={() => router.push("/")}>Dashboard</button><button className="ghost-button" onClick={() => { clearTokens(); router.replace("/login"); }}>Sign out</button></div></header>
      <section className="hero"><div className="eyebrow">LISTENING PRACTICE</div><h1>Train attention and accuracy.</h1><p>Move through IELTS-style listening sections, answer each question, and review your score after submission.</p></section>
      {error && <div className="error-box page-message">{error}</div>}
      <section className="test-grid">
        {tests.map((test) => <article className="test-card" key={test.id}>
          <div className="pill-row"><span className="pill">{test.difficulty}</span><span className="pill">Listening practice</span></div>
          <h2>{test.title}</h2><p className="muted">{test.description || "IELTS Listening practice test."}</p>
          <div className="test-meta"><span>{test.sections.length} sections</span><span>{test.sections.reduce((n, s) => n + s.questions.length, 0)} questions</span><span>{test.time_limit_minutes} min</span></div>
          <div className="listening-mode-actions"><button className="primary-button" disabled={busy} onClick={() => startTest(test, "practice")}>{busy ? "Starting…" : "Practice mode"}</button><button className="secondary-button" disabled={busy} onClick={() => startTest(test, "exam")}>{busy ? "Starting…" : "Exam mode"}</button></div>
        </article>)}
        {!tests.length && !error && <div className="empty-card">No Listening practice tests are available yet. Please check back soon.</div>}
      </section>
    </main>
  );

  if (view === "results" && selectedTest && detail && result) return (
    <main className="app-shell">
      <header className="topbar"><div><div className="brand">AI IELTS Coach</div><span className="muted">Listening results</span></div><div className="top-actions"><button className="ghost-button" onClick={() => router.push("/")}>Dashboard</button><button className="ghost-button" onClick={() => setView("select")}>Back to tests</button></div></header>
      <section className="result-hero"><div><div className="eyebrow">PRACTICE COMPLETE</div><h1>Your Listening review</h1><p className="muted">Review every answer and explanation. The band is an estimate based on this practice score.</p></div><div className="overall-band"><span>Estimated band</span><strong>{result.band_score}</strong><small>{result.score}/{result.total_questions} correct</small></div></section>
      <section className="review-list">
        {selectedTest.sections.map((s, si) => <article className="result-card" key={s.id}>
          <div className="review-passage-title"><span className="eyebrow">SECTION {si + 1}</span><h2>{s.title}</h2><span className="muted">{detail.answers.filter((a) => a.section_title === s.title && a.is_correct).length}/{s.questions.length} correct</span></div>
          {s.questions.map((q, i) => {
            const answer = detail.answers.find((a) => a.question_id === q.id);
            return <div className="review-question" key={q.id}>
              <div><strong>Question {i + 1}</strong><span className="question-type">{displayType(q.question_type)}</span></div>
              <p>{q.question_text}</p>
              <div className={answer?.is_correct ? "answer-row correct" : "answer-row incorrect"}><span>Your answer</span><strong>{answer?.user_answer || "Not answered"}</strong></div>
              <div className="answer-row"><span>Correct answer</span><strong>{answer?.correct_answer ?? "—"}</strong></div>
              {answer?.explanation && <div className="prompt-card review-explanation"><strong>Why this is correct</strong><p>{answer.explanation}</p></div>}
            </div>;
          })}
        </article>)}
      </section>
    </main>
  );

  const section = sections[activeSection];
  return (
    <main className="app-shell test-shell">
      <header className="topbar">
        <div><div className="brand">AI IELTS Coach</div><span className="muted">{selectedTest?.title}</span></div>
        <div className="top-actions"><button className="ghost-button" onClick={() => router.push("/")}>Dashboard</button><div className={secondsLeft <= 300 ? "timer danger" : "timer"}>{formatTime(secondsLeft)}</div></div>
      </header>
      <div className="skill-test-layout">
        <aside className="passage-sidebar">
          <div className="sidebar-label">{mode === "exam" ? "Exam sections" : "Practice sections"}</div>
          {sections.map((s, i) => <button key={s.id} disabled={mode === "exam" && !!audioPlayedSections[s.id] && !audioEndedSections[s.id] && i !== activeSection} className={i === activeSection ? "task-tab active" : "task-tab"} onClick={() => setActiveSection(i)}>
            <span>Section {i + 1}</span><small>{s.questions.length} questions</small>
          </button>)}
          <div className="progress-box"><strong>{answered}/{allQuestions.length}</strong><span>answered</span></div>
          <button className="submit-button" disabled={busy} onClick={() => void submitTest(false)}>{busy ? "Submitting…" : "Submit test"}</button>
        </aside>
        <section className="reading-workspace">
          {section && <><div className="skill-workspace-head"><div><span className="eyebrow">SECTION {activeSection + 1}</span><h1>{section.title}</h1></div><span>{section.questions.length} questions</span></div>
            {section.audio_url ? (
              <div className="listening-audio-card">
                <div>
                  <span className="eyebrow">LISTENING AUDIO</span>
                  <strong>Section {activeSection + 1} recording</strong>
                  <span className="muted">{mode === "exam" ? "Exam mode: one play-through per section. Pausing and resuming is allowed, but replay is disabled after the recording ends." : "Practice mode: play, pause, and replay the recording as often as you need."}</span>
                </div>
                <div className="listening-player-controls">
                  <audio ref={audioRef} className="listening-audio" preload="metadata" src={section.audio_url} onPlay={() => { setAudioPlaying(true); setAudioPlayedSections((current) => ({ ...current, [section.id]: true })); }} onPause={() => setAudioPlaying(false)} onEnded={() => { setAudioPlaying(false); setAudioEndedSections((current) => ({ ...current, [section.id]: true })); }} onError={() => { setAudioPlaying(false); setAudioPlayedSections((current) => ({ ...current, [section.id]: false })); setError("Audio could not be loaded. Check your connection and try again."); }} />
                  <button className="primary-button" disabled={mode === "exam" && !!audioEndedSections[section.id]} onClick={() => { const audio = audioRef.current; if (!audio) return; if (audio.paused) { if (mode === "exam" && audioEndedSections[section.id]) return; if (mode === "practice" && audioEndedSections[section.id]) { audio.currentTime = 0; setAudioEndedSections((current) => ({ ...current, [section.id]: false })); } void audio.play().catch(() => setError("Audio playback failed. Please check your connection and try again.")); } else audio.pause(); }}>{audioPlaying ? "Pause audio" : audioEndedSections[section.id] ? "Recording finished" : audioPlayedSections[section.id] ? "Resume audio" : "Play audio"}</button>
                  {mode === "exam" && audioEndedSections[section.id] && <span className="muted">This recording has ended and cannot be replayed in exam mode.</span>}
                </div>
              </div>
            ) : (
              <div className="listening-notice"><strong>Audio not configured</strong><span>This section does not have an audio asset yet. Add an audio URL to the section content to enable playback.</span></div>
            )}
            {section.instructions && <div className="prompt-card"><strong>Instructions</strong><p>{section.instructions}</p></div>}
            <div className="question-list">{section.questions.map((q, i) => <Question key={q.id} number={i + 1} question={q} value={answers[q.id] ?? ""} onChange={(value) => setAnswers((current) => ({ ...current, [q.id]: value }))} />)}</div>
          </>}
        </section>
      </div>
      {error && <div className="floating-error">{error}</div>}
    </main>
  );
}

function Question({ number, question, value, onChange }: {
  number: number;
  question: ListeningTest["sections"][number]["questions"][number];
  value: string;
  onChange: (value: string) => void;
}) {
  const options = Array.isArray(question.options) ? question.options : [];
  return <article className="question-card">
    <div className="question-card-head"><strong>Question {number}</strong><span className="question-type">{displayType(question.question_type)}</span></div>
    <p>{question.question_text}</p>
    {options.length ? <div className="option-list">{options.map((option, i) => {
      const text = String(option);
      return <label className={value === text ? "option selected" : "option"} key={i}><input type="radio" name={question.id} value={text} checked={value === text} onChange={(e) => onChange(e.target.value)} /><span>{text}</span></label>;
    })}</div> : <input className="answer-input" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Type your answer" />}
  </article>;
}
