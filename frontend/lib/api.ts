const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

type TokenPair = { access_token: string; refresh_token: string; token_type: string };

export function getAccessToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function saveTokens(tokens: TokenPair) {
  localStorage.setItem("access_token", tokens.access_token);
  localStorage.setItem("refresh_token", tokens.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function refreshToken() {
  const refresh_token = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
  if (!refresh_token) return false;

  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token }),
  });
  if (!response.ok) return false;

  const tokens = (await response.json()) as TokenPair;
  saveTokens(tokens);
  return true;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const access = getAccessToken();
  if (access) headers.set("Authorization", `Bearer ${access}`);

  let response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401 && retry && await refreshToken()) {
    return apiFetch<T>(path, options, false);
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {}
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type WritingTask = {
  id: string;
  task_number: number;
  task_type: string;
  prompt: string;
  instructions?: string | null;
  minimum_words: number;
  order: number;
};

export type WritingTest = {
  id: string;
  title: string;
  description?: string | null;
  test_type: string;
  difficulty: string;
  time_limit_minutes: number;
  tasks: WritingTask[];
};

export type AttemptStart = {
  attempt_id: string;
  writing_test_id: string;
  started_at: string;
  status: string;
};

export type DraftResponse = {
  submission_id: string;
  attempt_id: string;
  task_id: string;
  response_text: string;
  word_count: number;
  minimum_words: number;
  below_minimum_words: boolean;
  submitted_at: string;
};

export type Evaluation = {
  id: string;
  task_response_band?: number | null;
  task_achievement_band?: number | null;
  coherence_band?: number | null;
  lexical_band?: number | null;
  grammar_band?: number | null;
  overall_band?: number | null;
  feedback?: string | null;
  strengths?: string[] | null;
  improvements?: string[] | null;
  evaluated_by: string;
  evaluated_at: string;
};

export type Submission = {
  id: string;
  task_id: string;
  response_text: string;
  word_count: number;
  submitted_at: string;
  evaluation?: Evaluation | null;
};

export type AttemptDetail = {
  attempt_id: string;
  writing_test_id: string;
  status: string;
  started_at: string;
  submitted_at?: string | null;
  overall_band?: number | null;
  submissions: Submission[];
};

export type SubmitResponse = {
  attempt_id: string;
  status: string;
  submitted_at: string;
  task_word_counts: Record<string, number>;
  below_minimum_tasks: number[];
};

export type EvaluateResponse = {
  submission_id: string;
  status: string;
  evaluation: Evaluation;
};