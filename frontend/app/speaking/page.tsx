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
  transcribeSpeakingAudio,
} from "../../lib/api";

type View = "select" | "test" | "results";
type Phase = "preparation" | "speaking";

function formatTime(seconds: number) {
  const safe = Math.max(0, seconds);
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
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
  const [micSupported, setMicSupported] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState<SpeakingSubmitResponse | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const responseStartedAtRef = useRef<number | null>(null);
  const transcriptRef = useRef<Record<string, string>>({});
  const audioChunksRef = useRef<Blob[]>([]);
  const transcriptionPromiseRef = useRef<Promise<string | null> | null>(null);
  const resolveTranscriptionRef = useRef<((value: string | null) => void) | null>(null);
  const lastRecordedBlobRef = useRef<Blob | null>(null);
  const discardRecordingRef = useRef(false);

  const activePart = useMemo(
    () => selectedTest?.parts.slice().sort((a, b) => a.order - b.order)[activeIndex] ?? null,
    [selectedTest, activeIndex]
  );

  useEffect(() => {
    transcriptRef.current = transcripts;
  }, [transcripts]);

  useEffect(() => {
    discardRecordingRef.current = false;
    void loadTests();
    setMicSupported(typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia));
    return () => {
      discardRecordingRef.current = true;
      const recorder = mediaRecorderRef.current;
      if (recorder?.state === "recording") recorder.stop();
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (view !== "test" || !activePart) return;
    setPhase(activePart.preparation_seconds > 0 ? "preparation" : "speaking");
    setSecondsLeft(activePart.preparation_seconds > 0 ? activePart.preparation_seconds : activePart.response_seconds);
    stopRecording();
  }, [activePart, view]);

  useEffect(() => {
    // Wait until the part-initialization effect has set its countdown. On the
    // first render secondsLeft is 0; transitioning here would skip preparation.
    if (view !== "test" || !activePart || secondsLeft <= 0) return;

    const timer = window.setTimeout(() => {
      if (secondsLeft <= 1) {
        if (phase === "preparation") {
          beginSpeaking();
        } else {
          void finishPart();
        }
      } else {
        setSecondsLeft((value) => Math.max(0, value - 1));
      }
    }, 1000);
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
    if (!activePart || recording || isTranscribing) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setMessage("Audio recording is unavailable in this browser. You can type your transcript.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      transcriptionPromiseRef.current = new Promise((resolve) => {
        resolveTranscriptionRef.current = resolve;
      });

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        if (discardRecordingRef.current) {
          stream.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
          mediaRecorderRef.current = null;
          resolveTranscriptionRef.current?.(null);
          return;
        }
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        lastRecordedBlobRef.current = blob;
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
        mediaRecorderRef.current = null;

        if (!blob.size) {
          resolveTranscriptionRef.current?.(null);
          return;
        }

        setIsTranscribing(true);
        setMessage("Transcribing your recording…");
        try {
          const result = await transcribeSpeakingAudio(blob);
          const transcript = result.transcript.trim();
          if (!transcript) throw new Error("No speech was detected. Please retry or type your transcript.");
          transcriptRef.current = { ...transcriptRef.current, [activePart.id]: transcript };
          setTranscripts((current) => ({ ...current, [activePart.id]: transcript }));
          setError("");
          setMessage("Audio transcribed. Review or edit your transcript before continuing.");
          resolveTranscriptionRef.current?.(transcript);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Transcription failed. You can type your transcript.");
          setMessage("Your audio was captured, but transcription failed. Retry or type your transcript.");
          resolveTranscriptionRef.current?.(null);
        } finally {
          setIsTranscribing(false);
          resolveTranscriptionRef.current = null;
        }
      };

      recorder.start();
      setRecording(true);
      setError("");
      setMessage("Recording is active. Stop when you finish speaking to transcribe your answer.");
    } catch {
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
      setRecording(false);
      setMessage("Microphone permission was not available. You can type your transcript.");
    }
  }

  async function stopRecording(): Promise<string | null> {
    const recorder = mediaRecorderRef.current;
    if (recorder?.state === "recording") {
      recorder.stop();
      setRecording(false);
      const pending = transcriptionPromiseRef.current;
      if (!pending) return null;
      const result = await pending;
      if (transcriptionPromiseRef.current === pending) transcriptionPromiseRef.current = null;
      return result;
    }
    if (transcriptionPromiseRef.current) {
      const pending = transcriptionPromiseRef.current;
      const result = await pending;
      if (transcriptionPromiseRef.current === pending) transcriptionPromiseRef.current = null;
      return result;
    }
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    setRecording(false);
    return null;
  }

  async function saveCurrentPart(transcriptOverride?: string): Promise<boolean> {
    if (!attempt || !activePart || saving) return false;
    const transcript = (transcriptOverride ?? transcriptRef.current[activePart.id] ?? "").trim();
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
    const transcribed = await stopRecording();
    const finalTranscript = transcribed ?? transcriptRef.current[activePart.id] ?? "";
    const saved = await saveCurrentPart(finalTranscript);
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

  async function retryTranscription() {
    const blob = lastRecordedBlobRef.current;
    if (!blob || !activePart || isTranscribing) return;
    setIsTranscribing(true);
    setError("");
    try {
      const result = await transcribeSpeakingAudio(blob);
      const transcript = result.transcript.trim();
      if (!transcript) throw new Error("No speech was detected. Please type your transcript.");
      transcriptRef.current = { ...transcriptRef.current, [activePart.id]: transcript };
      setTranscripts((current) => ({ ...current, [activePart.id]: transcript }));
      setMessage("Audio transcribed. Review or edit your transcript before continuing.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transcription failed.");
    } finally {
      setIsTranscribing(false);
    }
  }

  function updateTranscript(value: string) {
    if (!activePart) return;
    transcriptRef.current = { ...transcriptRef.current, [activePart.id]: value };
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
          <p>Move through Parts 1, 2 and 3 with preparation time, timed speaking, microphone recording and automatic transcription.</p>
        </section>
        {error && <div role="alert" className="error-box page-message">{error}</div>}
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
          {!tests.length && !error && <div className="empty-card">No Speaking practice tests are available yet. Please check back soon.</div>}
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
          <div><div className="eyebrow">TEST COMPLETE</div><h1>Your Speaking review</h1><p role="status" aria-live="polite" className="muted">{submitted?.status === "evaluated" ? "All three parts have been evaluated." : "Your responses were submitted successfully."}</p>
            {error && <div role="alert" className="error-box page-message">{error}</div>}</div>
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
              <div className="record-visual"><div className={recording ? "mic-orb active" : "mic-orb"}>🎙️</div><div><strong>{recording ? "Speak naturally" : isTranscribing ? "Transcribing audio…" : "Recording stopped"}</strong><span>{isTranscribing ? "Your audio is being converted to text." : "Your recording is transcribed after you stop."}</span></div></div>
              <textarea value={transcripts[activePart.id] ?? ""} onChange={(e) => updateTranscript(e.target.value)} placeholder="Your transcript will appear here. You can edit it if needed…" />
              <div className="record-actions">
                <button className={recording ? "record-button active" : "record-button"} onClick={() => recording ? stopRecording() : void startRecording()}>{recording ? "Stop recording" : "Start recording"}</button>
                <button className="primary-button" disabled={saving || busy || isTranscribing || !(transcripts[activePart.id] ?? "").trim()} onClick={() => void finishPart()}>{activeIndex === (selectedTest?.parts.length ?? 1) - 1 ? "Finish test" : "Save & continue"}</button>
              </div>
              {isTranscribing && <p className="browser-note" role="status">Please wait while your recording is transcribed.</p>}
              {!micSupported && <p className="browser-note">Microphone access is unavailable here. You can still type or paste your transcript.</p>}
              {lastRecordedBlobRef.current && !recording && !isTranscribing && error && <button className="ghost-button" onClick={() => void retryTranscription()}>Retry transcription</button>}
            </div>
          )}
        </>}
      </section>
      {error && <div role="alert" className="floating-error">{error}</div>}
      {message && <div role="status" aria-live="polite" className="floating-message">{message}</div>}
    </main>
  );
}

function Score({ label, value }: { label: string; value?: number | null }) {
  return <div className="score-item"><span>{label}</span><strong>{value ?? "—"}</strong></div>;
}
