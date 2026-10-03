"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, clearTokens, SkillAttempt } from "../lib/api";

type Skill = "Reading" | "Listening" | "Writing" | "Speaking";

const skillMeta: Record<Skill, { route: string; description: string; icon: string }> = {
  Reading: { route: "/reading", description: "Build speed, accuracy and question-type confidence.", icon: "R" },
  Listening: { route: "/listening", description: "Train attention, spelling and answer prediction.", icon: "L" },
  Writing: { route: "/writing", description: "Practise both tasks and get AI criterion feedback.", icon: "W" },
  Speaking: { route: "/speaking", description: "Practise Parts 1–3 with timed responses and AI feedback.", icon: "S" },
};

function bandValue(attempts: SkillAttempt[]) {
  const bands = attempts.map((a) => a.band_score ?? a.overall_band).filter((x): x is number => typeof x === "number");
  return bands.length ? bands[0] : null;
}

function latestDate(attempts: SkillAttempt[]) {
  const dates = attempts.map((a) => a.submitted_at).filter(Boolean) as string[];
  return dates.length ? new Date(dates[0]) : null;
}

function formatDate(date: Date | null) {
  if (!date) return "No attempts yet";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<Record<Skill, SkillAttempt[]>>({
    Reading: [], Listening: [], Writing: [], Speaking: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const [reading, listening, writing, speaking] = await Promise.all([
        apiFetch<SkillAttempt[]>("/reading/attempts"),
        apiFetch<SkillAttempt[]>("/listening/attempts"),
        apiFetch<SkillAttempt[]>("/writing/attempts"),
        apiFetch<SkillAttempt[]>("/speaking/attempts"),
      ]);
      setData({
        Reading: reading,
        Listening: listening,
        Writing: writing,
        Speaking: speaking,
      });
    } catch (err) {
      if (String(err).includes("401")) {
        clearTokens();
        router.replace("/login");
        return;
      }
      setError(err instanceof Error ? err.message : "Could not load your dashboard.");
    } finally {
      setLoading(false);
    }
  }

  const allAttempts = useMemo(
    () => (Object.entries(data) as [Skill, SkillAttempt[]][])
      .flatMap(([skill, attempts]) => attempts.map((attempt) => ({ skill, attempt })))
      .filter(({ attempt }) => attempt.submitted_at)
      .sort((a, b) => new Date(b.attempt.submitted_at!).getTime() - new Date(a.attempt.submitted_at!).getTime()),
    [data]
  );

  const completedSkills = (Object.keys(data) as Skill[]).filter((skill) => data[skill].some((a) => a.submitted_at)).length;
  const scoredBands = (Object.values(data).flat() as SkillAttempt[])
    .map((a) => a.band_score ?? a.overall_band)
    .filter((x): x is number => typeof x === "number");
  const averageBand = scoredBands.length ? Math.round((scoredBands.reduce((a, b) => a + b, 0) / scoredBands.length) * 2) / 2 : null;

  return (
    <main className="dashboard-shell">
      <header className="topbar dashboard-topbar">
        <button className="brand brand-button" onClick={() => router.push("/")}>AI IELTS Coach</button>
        <nav className="dashboard-nav">
          <span className="nav-active">Dashboard</span>
          <button onClick={() => router.push("/writing")}>Practice</button>
        </nav>
        <button className="ghost-button" onClick={() => { clearTokens(); router.replace("/login"); }}>Sign out</button>
      </header>

      <div className="dashboard-content">
        <section className="dashboard-welcome">
          <div>
            <div className="eyebrow">YOUR IELTS WORKSPACE</div>
            <h1>Keep building your score.</h1>
            <p>Choose a skill to practise, review your latest performance, and keep your preparation moving.</p>
          </div>
          <button className="primary-button dashboard-cta" onClick={() => router.push("/writing")}>Start a practice test →</button>
        </section>

        {error && <div className="error-box">{error}</div>}

        <section className="dashboard-summary">
          <div><span>Skills practised</span><strong>{completedSkills}<small>/4</small></strong></div>
          <div><span>Practice attempts</span><strong>{allAttempts.length}</strong></div>
          <div><span>Average recorded band</span><strong>{averageBand ?? "—"}</strong></div>
        </section>

        <section>
          <div className="section-heading"><div><div className="eyebrow">FOUR SKILLS</div><h2>Your practice areas</h2></div></div>
          <div className="skill-grid">
            {(Object.keys(skillMeta) as Skill[]).map((skill) => {
              const attempts = data[skill];
              const latest = attempts.find((a) => a.submitted_at);
              const band = latest ? bandValue([latest]) : null;
              return (
                <article className="dashboard-skill-card" key={skill} onClick={() => router.push(skillMeta[skill].route)}>
                  <div className="skill-card-top"><span className="skill-icon">{skillMeta[skill].icon}</span><span className="skill-arrow">→</span></div>
                  <h3>{skill}</h3>
                  <p>{skillMeta[skill].description}</p>
                  <div className="skill-card-bottom">
                    <span>{attempts.filter((a) => a.submitted_at).length} completed</span>
                    <strong>{band !== null ? `Band ${band}` : "Start now"}</strong>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="activity-section">
          <div className="section-heading"><div><div className="eyebrow">RECENT ACTIVITY</div><h2>Keep an eye on your progress</h2></div></div>
          {loading ? <div className="empty-dashboard">Loading your practice history…</div> :
            allAttempts.length === 0 ? (
              <div className="empty-dashboard"><strong>Your first practice test is waiting.</strong><span>Start with any skill above. Results will appear here after submission.</span></div>
            ) : (
              <div className="activity-list">
                {allAttempts.slice(0, 6).map(({ skill, attempt }) => {
                  const band = attempt.band_score ?? attempt.overall_band;
                  return <button className="activity-row" key={`${skill}-${attempt.attempt_id}`} onClick={() => router.push(skillMeta[skill].route)}>
                    <span className="activity-icon">{skillMeta[skill].icon}</span>
                    <span className="activity-main"><strong>{skill} practice</strong><small>{formatDate(new Date(attempt.submitted_at!))}</small></span>
                    <span className="activity-score">{band !== null && band !== undefined ? `Band ${band}` : "Submitted"}</span>
                    <span className="skill-arrow">→</span>
                  </button>;
                })}
              </div>
            )
          }
        </section>
      </div>
    </main>
  );
}
