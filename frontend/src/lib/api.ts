import type {
  AssetSummary,
  Candidate,
  ComplianceReport,
  ControlSummary,
  FindingSummary,
  Health,
  DbHealth,
  OptimizationResponse,
  Overview,
  PortfolioOutcome,
  RunParams,
  ScenarioSummary,
  SimulationResponse,
} from "@/types/api";

/**
 * Empty by default: requests go to the same origin and Next.js rewrites them to the API
 * (see next.config.ts). That keeps one image working on localhost, behind a tunnel, or on a
 * deployed host without a rebuild. Set NEXT_PUBLIC_API_BASE_URL only to point the browser at
 * a *different* origin than the page itself.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${path} -> HTTP ${res.status}${detail ? `: ${detail}` : ""}`);
  }
  return (await res.json()) as T;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  health: () => request<Health>("/health"),
  healthDb: () => request<DbHealth>("/health/db"),

  overview: () => request<Overview>("/api/v1/overview"),
  assets: () => request<AssetSummary[]>("/api/v1/assets"),
  findings: () => request<FindingSummary[]>("/api/v1/findings"),
  controls: () => request<ControlSummary[]>("/api/v1/controls"),
  scenarios: () => request<ScenarioSummary[]>("/api/v1/scenarios"),
  candidates: () => request<Candidate[]>("/api/v1/candidates"),

  compliance: (params: RunParams = {}) =>
    request<ComplianceReport>(
      `/api/v1/compliance?n_trials=${params.n_trials ?? 10_000}&seed=${params.seed ?? 42}`,
    ),

  aiStatus: () =>
    request<{
      enabled: boolean;
      providers: { id: string; label: string; model: string; available: boolean }[];
      active: string[];
      fallback: string;
      max_steps: number;
    }>("/api/v1/ai/status"),

  ask: (question: string) =>
    post<{
      question: string;
      answer: string;
      provider: string;
      model: string;
      steps: number;
      tool_calls: { name: string; arguments: Record<string, unknown>; ok: boolean }[];
      grounding: { grounded: boolean; unverified_numbers: string[]; note: string };
      degraded: boolean;
      reason: string | null;
      available_providers: string[];
    }>("/api/v1/ask", { question }),

  simulateScenario: (
    scenarioId: string,
    params: RunParams & { controls?: string[] } = {},
  ) =>
    post<SimulationResponse>(`/api/v1/scenarios/${scenarioId}/simulate`, {
      n_trials: params.n_trials ?? 10_000,
      seed: params.seed ?? 42,
      controls: params.controls ?? [],
    }),

  simulatePortfolio: (params: RunParams & { controls?: string[] } = {}) =>
    post<PortfolioOutcome>("/api/v1/portfolio/simulate", {
      n_trials: params.n_trials ?? 10_000,
      seed: params.seed ?? 42,
      controls: params.controls ?? [],
    }),

  optimize: (budget: number, params: RunParams = {}) =>
    post<OptimizationResponse>("/api/v1/optimize", {
      budget,
      n_trials: params.n_trials ?? 10_000,
      seed: params.seed ?? 42,
    }),

  delay: (
    scenarioId: string,
    params: RunParams & { controls: string[]; days: number },
  ) =>
    post<{
      scenario_id: string;
      days: number;
      window_years: number;
      loss_if_delayed: number;
      loss_if_remediated_now: number;
      avoidable_loss: number;
      currency: string;
      method: string;
    }>(`/api/v1/what-if/scenarios/${scenarioId}/delay`, {
      n_trials: params.n_trials ?? 10_000,
      seed: params.seed ?? 42,
      controls: params.controls,
      days: params.days,
    }),

  criticality: (
    scenarioId: string,
    overrides: Record<string, number>,
    params: RunParams = {},
  ) =>
    post<{
      scenario_id: string;
      eal_before: number;
      eal_after: number;
      eal_delta: number;
      before: { score: number; band: string };
      after: { score: number; band: string };
      currency: string;
    }>(`/api/v1/what-if/scenarios/${scenarioId}/criticality`, {
      n_trials: params.n_trials ?? 10_000,
      seed: params.seed ?? 42,
      overrides,
    }),
};
