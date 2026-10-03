"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  apiFetch,
  clearTokens,
  SpeakingAttemptDetail,
  SpeakingAttemptStart,
  SpeakingDraft,
  SpeakingEvaluation,
  SpeakingPart,
  SpeakingSubmitResponse,
  SpeakingTest,
  SpeakingEvaluateResponse,
} from "../../lib/api";

type View = "select" | "test" | "results";
type Phase = "preparation" | "speaking";

type SpeechRecognitionEventLike = Event & {
  results: {
    length: number;
    [index: number]: { [index: number]: { transcript: string } };
  };
};
type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: Event) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

function formatTime(seconds: number) {
  const safe = Math.max(0, seconds);
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}

function getSpeechRecognition() {
  if (typeof window === "undefined") return null;
  const browser = window as typeof window & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  const Constructor = browser.SpeechRecognition ?? browser.webkitSpeechRecognition;
  return Constructor ? new Constructor() : null;
}

export default function SpeakingPage() {
  const router = useRouter();
  const [view, setView] = useState<View>("select");
  const [tests, setTests] = useState<SpeakingTest[]>([]);
  const [selectedTest, setSelectedTest] = useState<SpeakingTest | null>(null);
  const [attempt, setAttempt] = useState<SpeakingAttemptStart | null>(null);
  const [attemptDetail, setAttemptDetail] = useState<SpeakingAttemptDetail | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("preparation");
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [transcripts, setTranscripts] = useState<Record<string, string>>({});
  const [drafts, setDrafts] = useState<Record<string, SpeakingDraft>>({});
  const [evaluations, setEvaluations] = useState<Record<string, SpeakingEvaluation>>({});
  const [recording, setRecording] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [micSupported, setMicSupported] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState<SpeakingSubmitResponse | null>(null);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const responseStartedAtRef = useRef<number | null>(null);
  const transcriptRef = useRef<Record<string, string>>({});

  const activePart = useMemo(
    () => selectedTest?.parts.slice().sort((a, b) => a.order - b.order)[activeIndex] ?? null,
    [selectedTest, activeIndex]
  );

  useEffect(() => {
    transcriptRef.current = transcripts;
  }, [transcripts]);

  useEffect(() => {
    void loadTests();
    setSpeechSupported(Boolean(getSpeechRecognition()));
    setMicSupported(typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia));
    return () => stopRecording();
  }, []);

  useEffect(() => {
    if (view !== "test" || !activePart) return;
    setPhase(activePart.preparation_seconds > 0 ? "preparation" : "speaking");
    setSecondsLeft(activePart.preparation_seconds > 0 ? activePart.preparation_seconds : activePart.response_seconds);
    setInterimTranscript("");
    stopRecording();
  }, [activePart, view]);

  useEffect(() => {
    if (view !== "test" || !activePart) return;
    if (secondsLeft <= 0) {
      if (phase === "preparation") {
        beginSpeaking();
      } else {
        void finishPart();
      }
      return;
    }

    const timer = window.setTimeout(() => setSecondsLeft((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [view, activePart, phase, secondsLeft]);

  async function loadTests() {
    try {
      setError("");
      setTests(await apiFetch<SpeakingTest[]>("/speaking/tests"));
    } catch (err) {
      if (String(err).includes("401")) {
        clearTokens();
        router.replace("/login");
      } else {
        setError(err instanceof Error ? err.message : "Could not load Speaking tests.");
      }
    }
  }

  async function startTest(test: SpeakingTest) {
    setBusy(true);
    setError("");
    try {
      const started = await apiFetch<SpeakingAttemptStart>(`/speaking/tests/${test.id}/start`, { method: "POST" });
      const ordered = test.parts.slice().sort((a, b) => a.order - b.order);
      setSelectedTest({ ...test, parts: ordered });
      setAttempt(started);
      setAttemptDetail(null);
      setTranscripts({});
      setDrafts({});
      setEvaluations({});
      setSubmitted(null);
      setActiveIndex(0);
      setView("test");
      setMessage("Test started. Part 1 begins with preparation.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start Speaking test.");
    } finally {
      setBusy(false);
    }
  }

  function beginSpeaking() {
    if (!activePart || phase === "speaking") return;
    setPhase("speaking");
    setSecondsLeft(activePart.response_seconds);
    responseStartedAtRef.current = Date.now();
    void startRecording();
  }

  async function startRecording() {
    if (!activePart || recording) return;
    const recognition = getSpeechRecognition();
    if (recognition) {
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";
      recognition.onresult = (event) => {
        let finalText = "";
        for (let i = 0; i < event.results.length; i += 1) {
          finalText += event.results[i][0].transcript;
        }
        setInterimTranscript("");
        setTranscripts((current) => ({ ...current, [activePart.id]: finalText.trim() }));
      };
      recognition.onerror = () => setMessage("Speech recognition stopped. You can continue with manual transcript editing.");
      recognition.onend = () => setRecording(false);
      recognitionRef.current = recognition;
      try {
        recognition.start();
      } catch {}
    }

    if (navigator.mediaDevices?.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
        const recorder = new MediaRecorder(stream);
        recorder.onstop = () => {
          stream.getTracks().forEach((track) => track.stop());
        };
        mediaRecorderRef.current = recorder;
        recorder.start();
      } catch {
        setMessage("Microphone permission was not available. Transcript mode is still usable.");
      }
    }
    setRecording(true);
    setMessage(speechSupported ? "Recording and live transcription are active." : "Recording is active. Type your transcript below if speech recognition is unavailable.");
  }

  function stopRecording() {
    try { recognitionRef.current?.stop(); } catch {}
    recognitionRef.current = null;
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    mediaRecorderRef.current = null;
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    setRecording(false);
  }

  async function saveCurrentPart(): Promise<boolean> {
    if (!attempt || !activePart || saving) return false;
    const transcript = transcriptRef.current[activePart.id]?.trim() ?? "";
    if (!transcript) {
      setError(`Part ${activePart.part_number} needs a transcript before you continue.`);
      return false;
    }

    setSaving(true);
    try {
      const elapsed = responseStartedAtRef.current ? Math.round((Date.now() - responseStartedAtRef.current) / 1000) : null;
      const saved = await apiFetch<SpeakingDraft>(`/speaking/attempts/${attempt.attempt_id}/parts/${activePart.id}`, {
        method: "PUT",
        body: JSON.stringify({ transcript, duration_seconds: elapsed }),
      });
      setDrafts((current) => ({ ...current, [activePart.id]: saved }));
      setMessage("Response saved.");
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save response.");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function finishPart() {
    stopRecording();
    const saved = await saveCurrentPart();
    if (!saved || !activePart || !selectedTest) return;
    const nextIndex = activeIndex + 1;
    if (nextIndex < selectedTest.parts.length) {
      setActiveIndex(nextIndex);
      return;
    }
    await submitTest();
  }

  async function submitTest() {
    if (!attempt || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await apiFetch<SpeakingSubmitResponse>(`/speaking/attempts/${attempt.attempt_id}/submit`, { method: "POST" });
      setSubmitted(result);
      const detail = await apiFetch<SpeakingAttemptDetail>(`/speaking/attempts/${attempt.attempt_id}`);
      setAttemptDetail(detail);
      setView("results");

      for (const response of detail.responses) {
        try {
          const evaluated = await apiFetch<SpeakingEvaluateResponse>(`/speaking/responses/${response.id}/evaluate`, { method: "POST" });
          setEvaluations((current) => ({ ...current, [response.part_id]: evaluated.evaluation }));
        } catch (err) {
          setError(err instanceof Error ? err.message : "AI evaluation failed.");
        }
      }

      const refreshed = await apiFetch<SpeakingAttemptDetail>(`/speaking/attempts/${attempt.attempt_id}`);
      setAttemptDetail(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit Speaking test.");
    } finally {
      setBusy(false);
    }
  }

  function updateTranscript(value: string) {
    if (!activePart) return;
    setTranscripts((current) => ({ ...current, [activePart.id]: value }));
  }

  function evaluationFor(part: SpeakingPart) {
    return evaluations[part.id] ?? attemptDetail?.responses.find((item) => item.part_id === part.id)?.evaluation ?? null;
  }

  if (view === "select") {
    return (
      <main className="app-shell">
        <header className="topbar">
          <div><div className="brand">AI IELTS Coach</div><span className="muted">Speaking</span></div>
          <div className="top-actions">
            <button className="ghost-button" onClick={() => router.push("/writing")}>Writing</button>
            <button className="ghost-button" onClick={() => { clearTokens(); router.replace("/login"); }}>Sign out</button>
          </div>
        </header>
        <section className="hero">
          <div className="eyebrow">SPEAKING PRACTICE</div>
          <h1>Practice like the real interview.</h1>
          <p>Move through Parts 1, 2 and 3 with preparation time, timed speaking, microphone recording and live transcript capture.</p>
        </section>
        {error && <div className="error-box page-message">{error}</div>}
        <section className="test-grid">
          {tests.map((test) => (
            <article className="test-card" key={test.id}>
              <div className="pill-row"><span className="pill">{test.test_type}</span><span className="pill">{test.difficulty}</span></div>
              <h2>{test.title}</h2>
              <p className="muted">{test.description || "IELTS Speaking practice test."}</p>
              <div className="test-meta"><span>{test.parts.length} parts</span><span>{test.time_limit_minutes} min</span></div>
              <button className="primary-button" disabled={busy} onClick={() => void startTest(test)}>{busy ? "Starting…" : "Start speaking test"}</button>
            </article>
          ))}
          {!tests.length && !error && <div className="empty-card">Loading available Speaking tests…</div>}
        </section>
      </main>
    );
  }

  if (view === "results" && selectedTest && attemptDetail) {
    return (
      <main className="app-shell">
        <header className="topbar">
          <div><div className="brand">AI IELTS Coach</div><span className="muted">Speaking results</span></div>
          <div className="top-actions">
            <button className="ghost-button" onClick={() => router.push("/writing")}>Writing</button>
            <button className="ghost-button" onClick={() => setView("select")}>Back to tests</button>
          </div>
        </header>
        <section className="result-hero speaking-result-hero">
          <div><div className="eyebrow">TEST COMPLETE</div><h1>Your Speaking review</h1><p className="muted">{submitted?.status === "evaluated" ? "All three parts have been evaluated." : "Your responses were submitted successfully."}</p></div>
          <div className="overall-band"><span>Overall</span><strong>{attemptDetail.overall_band ?? "—"}</strong></div>
        </section>
        <div className="results-grid">
          {selectedTest.parts.map((part) => {
            const evaluation = evaluationFor(part);
            const response = attemptDetail.responses.find((item) => item.part_id === part.id);
            return (
              <article className="result-card" key={part.id}>
                <div className="result-card-head">
                  <div><span className="eyebrow">PART {part.part_number}</span><h2>{part.title}</h2></div>
                  <strong className="score">{evaluation?.overall_band ?? "—"}</strong>
                </div>
                <div className="score-grid speaking-score-grid">
                  <Score label="Fluency & Coherence" value={evaluation?.fluency_band} />
                  <Score label="Lexical Resource" value={evaluation?.lexical_band} />
                  <Score label="Grammar" value={evaluation?.grammar_band} />
                  <Score label="Pronunciation" value={evaluation?.pronunciation_band} />
                </div>
                <details className="transcript-details">
                  <summary>View transcript</summary>
                  <p>{response?.transcript || "No transcript available."}</p>
                </details>
                {evaluation ? <>
                  <div className="feedback"><h3>AI feedback</h3><p>{evaluation.feedback || "No summary provided."}</p></div>
                  <div className="feedback-columns"><div><h3>Strengths</h3><ul>{(evaluation.strengths ?? []).map((item, i) => <li key={i}>{item}</li>)}</ul></div><div><h3>Improve next</h3><ul>{(evaluation.improvements ?? []).map((item, i) => <li key={i}>{item}</li>)}</ul></div></div>
                </> : <div className="pending-box">AI evaluation is unavailable. Your response is saved.</div>}
              </article>
            );
          })}
        </div>
      </main>
    );
  }

  return (
    <main className="app-shell speaking-shell">
      <header className="topbar">
        <div><div className="brand">AI IELTS Coach</div><span className="muted">{selectedTest?.title}</span></div>
        <div className="speaking-timer-wrap">
          <span className="phase-label">{phase === "preparation" ? "PREPARE" : "SPEAK"}</span>
          <div className={secondsLeft <= 10 ? "timer danger" : "timer"}>{formatTime(secondsLeft)}</div>
        </div>
      </header>

      <div className="speaking-progress">
        {selectedTest?.parts.map((part, index) => (
          <div className={index === activeIndex ? "progress-part active" : index < activeIndex ? "progress-part done" : "progress-part"} key={part.id}>
            <span>Part {part.part_number}</span><small>{index < activeIndex ? "Complete" : index === activeIndex ? "Current" : "Upcoming"}</small>
          </div>
        ))}
      </div>

      <section className="speaking-stage">
        {activePart && <>
          <div className="stage-heading">
            <div><span className="eyebrow">PART {activePart.part_number}</span><h1>{activePart.title}</h1></div>
            <div className={recording ? "recording-badge live" : "recording-badge"}><span className="record-dot" />{recording ? "Recording" : "Ready"}</div>
          </div>

          <div className="speaking-prompt">
            <div className="prompt-kicker">{phase === "preparation" ? "Get ready" : "Your question"}</div>
            <h2>{activePart.prompt}</h2>
            {activePart.instructions && <p>{activePart.instructions}</p>}
          </div>

          {phase === "preparation" ? (
            <div className="prep-panel">
              <div className="countdown-ring"><strong>{secondsLeft}</strong><span>seconds</span></div>
              <div><h2>Prepare your answer</h2><p className="muted">Think of 2–3 ideas and a simple example. Speaking starts automatically when the countdown ends.</p></div>
              <button className="primary-button" onClick={beginSpeaking}>Start speaking now</button>
            </div>
          ) : (
            <div className="record-panel">
              <div className="record-visual"><div className={recording ? "mic-orb active" : "mic-orb"}>🎙️</div><div><strong>{recording ? "Speak naturally" : "Recording paused"}</strong><span>{speechSupported ? "Live transcript is being captured." : "Live speech recognition is not available in this browser."}</span></div></div>
              <textarea value={transcripts[activePart.id] ?? ""} onChange={(e) => updateTranscript(e.target.value)} placeholder="Your transcript will appear here. You can edit it if needed…" />
              {interimTranscript && <div className="interim-text">{interimTranscript}</div>}
              <div className="record-actions">
                <button className={recording ? "record-button active" : "record-button"} onClick={() => recording ? stopRecording() : void startRecording()}>{recording ? "Stop recording" : "Start recording"}</button>
                <button className="primary-button" disabled={saving || busy || !(transcripts[activePart.id] ?? "").trim()} onClick={() => void finishPart()}>{activeIndex === (selectedTest?.parts.length ?? 1) - 1 ? "Finish test" : "Save & continue"}</button>
              </div>
              {!micSupported && <p className="browser-note">Microphone access is unavailable here. You can still type or paste your transcript.</p>}
            </div>
          )}
        </>}
      </section>
      {error && <div className="floating-error">{error}</div>}
      {message && <div className="floating-message">{message}</div>}
    </main>
  );
}

function Score({ label, value }: { label: string; value?: number | null }) {
  return <div className="score-item"><span>{label}</span><strong>{value ?? "—"}</strong></div>;
}
