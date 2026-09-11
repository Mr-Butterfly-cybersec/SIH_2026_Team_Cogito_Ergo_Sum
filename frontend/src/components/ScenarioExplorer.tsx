"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { LossExceedance, LossHistogram } from "@/components/charts/LossCharts";
import {
  Badge,
  CandidateChip,
  Card,
  EmptyState,
  ErrorState,
  SegmentedControl,
  ShareBar,
  Skeleton,
  Stat,
} from "@/components/ui";
import { api } from "@/lib/api";
import { CONFIDENCE_COLOR, decimal, inrShort, pct } from "@/lib/format";

const TRIAL_OPTIONS = [
  { label: "Fast", value: 5_000, hint: "5,000 trials — quickest" },
  { label: "Balanced", value: 20_000, hint: "20,000 trials — default" },
  { label: "Precise", value: 60_000, hint: "60,000 trials — tighter tail estimates" },
];

export function ScenarioExplorer() {
  const [pickedId, setPickedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [trials, setTrials] = useState(20_000);
  const [delayDays, setDelayDays] = useState(30);

  const scenariosQuery = useQuery({ queryKey: ["scenarios"], queryFn: api.scenarios });
  const candidatesQuery = useQuery({ queryKey: ["candidates"], queryFn: api.candidates });

  const scenarios = scenariosQuery.data ?? [];
  const activeId = pickedId ?? scenarios[0]?.id ?? null;
  const active = scenarios.find((s) => s.id === activeId) ?? null;

  const selectionKey = useMemo(() => [...selected].sort().join("|"), [selected]);

  const hardened = useQuery({
    queryKey: ["simulate", activeId, selectionKey, trials],
    queryFn: () =>
      api.simulateScenario(activeId as string, { controls: selected, n_trials: trials }),
    enabled: Boolean(activeId),
  });

  const baseline = useQuery({
    queryKey: ["simulate", activeId, "", trials],
    queryFn: () => api.simulateScenario(activeId as string, { controls: [], n_trials: trials }),
    enabled: Boolean(activeId),
  });

  const delay = useMutation({
    mutationFn: () =>
      api.delay(activeId as string, {
        controls: selected,
        days: delayDays,
        n_trials: trials,
      }),
  });

  const criticality = useMutation({
    mutationFn: () =>
      api.criticality(
        activeId as string,
        { availability: 5, integrity: 5, confidentiality: 5, regulatory: 5 },
        { n_trials: trials },
      ),
  });

  const relevantCandidates = useMemo(() => {
    if (!active) return [];
    return (candidatesQuery.data ?? [])
      .filter((candidate) => candidate.scenarios.includes(active.id))
      .sort((a, b) => b.effectiveness_gain - a.effectiveness_gain);
  }, [active, candidatesQuery.data]);

  const maxEal = Math.max(1, ...scenarios.map((s) => s.baseline_eal ?? 0));
  const before = baseline.data?.summary;
  const after = hardened.data?.summary;
  const reduction = before && after ? before.eal - after.eal : 0;
  const reductionPct = before && before.eal > 0 ? (reduction / before.eal) * 100 : 0;

  function pickScenario(id: string) {
    setPickedId(id);
    setSelected([]);
    delay.reset();
    criticality.reset();
  }

  function toggleControl(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
    delay.reset();
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <Card
        title={`Scenarios · ${scenarios.length}`}
        className="h-fit lg:sticky lg:top-4"
        action={
          scenariosQuery.isFetching ? (
            <span className="text-[10px] text-slate-500" aria-live="polite">
              loading…
            </span>
          ) : null
        }
      >
        {scenariosQuery.isError ? (
          <ErrorState
            message="Could not load the scenario catalogue."
            onRetry={() => scenariosQuery.refetch()}
            compact
          />
        ) : scenariosQuery.isLoading ? (
          <div className="space-y-2">
            {[0, 1, 2, 3, 4].map((row) => (
              <Skeleton key={row} className="h-[58px] w-full rounded-lg" />
            ))}
          </div>
        ) : scenarios.length === 0 ? (
          <EmptyState>No scenarios are modelled for this organization yet.</EmptyState>
        ) : (
          <>
            <p className="mb-3 text-[11px] leading-snug text-slate-500">
              Ranked by current-posture exposure. Select one to open it in place.
            </p>
            <ul className="max-h-[560px] space-y-1 overflow-y-auto pr-1">
              {scenarios.map((scenario) => {
                const isActive = scenario.id === activeId;
                const share = ((scenario.baseline_eal ?? 0) / maxEal) * 100;
                return (
                  <li key={scenario.id}>
                    <button
                      type="button"
                      onClick={() => pickScenario(scenario.id)}
                      aria-current={isActive ? "true" : undefined}
                      className={`hover-lift w-full rounded-lg border px-3 py-2 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-cyan-400 ${
                        isActive
                          ? "border-cyan-400/50 bg-cyan-500/10"
                          : "border-transparent hover:border-white/15 hover:bg-white/[0.03]"
                      }`}
                    >
                      <div className="flex items-baseline justify-between gap-2">
                        <span
                          className={`line-clamp-2 text-[12px] font-medium leading-snug ${
                            isActive ? "text-cyan-100" : "text-slate-200"
                          }`}
                        >
                          {scenario.name}
                        </span>
                        <span className="shrink-0 font-mono text-[11px] text-slate-400">
                          {inrShort(scenario.baseline_eal ?? 0)}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate text-[10px] text-slate-500">
                        {scenario.asset_name ?? scenario.id}
                      </p>
                      <div className="mt-2">
                        <ShareBar value={share} max={100} tone={isActive ? "active" : "neutral"} />
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </Card>

      <div className="min-w-0 space-y-4">
        {active ? (
          <Card className="min-w-0">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-semibold text-white">{active.name}</h2>
                  <Badge className="border-white/15 bg-white/5 text-slate-400">{active.id}</Badge>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {active.asset_name ?? "Unassigned asset"}
                  {active.category ? ` · ${active.category}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {active.max_cvss !== null ? (
                  <Badge className="border-orange-500/40 bg-orange-500/10 text-orange-300">
                    CVSS {active.max_cvss.toFixed(1)}
                  </Badge>
                ) : null}
                {active.max_epss !== null ? (
                  <Badge className="border-fuchsia-500/40 bg-fuchsia-500/10 text-fuchsia-300">
                    EPSS {(active.max_epss * 100).toFixed(1)}%
                  </Badge>
                ) : null}
                {hardened.data ? (
                  <Badge
                    className={
                      CONFIDENCE_COLOR[hardened.data.evidence_mix.band] ??
                      "border-white/15 text-slate-400"
                    }
                  >
                    {hardened.data.evidence_mix.band} confidence
                  </Badge>
                ) : null}
              </div>
            </div>

            {baseline.isError || hardened.isError ? (
              <ErrorState
                message="The simulation for this scenario failed."
                onRetry={() => {
                  baseline.refetch();
                  hardened.refetch();
                }}
              />
            ) : null}

            <div className="mt-4 grid grid-cols-2 gap-4 border-t border-white/5 pt-4 sm:grid-cols-3 lg:grid-cols-6">
              <Stat
                label="EAL"
                value={after ? inrShort(after.eal) : "…"}
                sub={selected.length ? `was ${before ? inrShort(before.eal) : "…"}` : "expected annual"}
                tone="accent"
              />
              <Stat label="P90" value={after ? inrShort(after.p90) : "…"} />
              <Stat label="P95" value={after ? inrShort(after.p95) : "…"} />
              <Stat label="CVaR 95" value={after ? inrShort(after.cvar_95) : "…"} />
              <Stat
                label="Vulnerability"
                value={hardened.data ? decimal(hardened.data.frequency.vulnerability) : "…"}
                sub="Pr(loss | threat event)"
              />
              <Stat
                label="Loss event freq"
                value={hardened.data ? decimal(hardened.data.frequency.mean_lef, 2) : "…"}
                sub="events / year"
              />
            </div>

            {selected.length > 0 && before && after ? (
              <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border border-emerald-500/25 bg-emerald-500/[0.07] px-4 py-3">
                <span className="text-[11px] uppercase tracking-wider text-emerald-300">
                  Applying {selected.length} control{selected.length > 1 ? "s" : ""}
                </span>
                <span className="font-mono text-sm text-emerald-200">
                  {inrShort(before.eal)} → {inrShort(after.eal)}
                </span>
                <span className="text-sm font-semibold text-emerald-300">
                  −{inrShort(reduction)} ({pct(reductionPct)})
                </span>
              </div>
            ) : null}

            <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
              {hardened.data ? (
                <>
                  <div className="min-w-0 rounded-xl border border-white/5 bg-black/20 p-3">
                    <p className="mb-2 text-[10px] uppercase tracking-[0.16em] text-slate-500">
                      Loss-exceedance curve · P(annual loss &gt; x)
                    </p>
                    <LossExceedance
                      lossExceedance={hardened.data.loss_exceedance}
                      summary={hardened.data.summary}
                    />
                  </div>
                  <div className="min-w-0 rounded-xl border border-white/5 bg-black/20 p-3">
                    <p className="mb-2 text-[10px] uppercase tracking-[0.16em] text-slate-500">
                      Simulated annual-loss distribution
                    </p>
                    <LossHistogram
                      histogram={hardened.data.histogram}
                      summary={hardened.data.summary}
                    />
                  </div>
                </>
              ) : (
                <div className="col-span-full h-[220px] animate-pulse rounded-xl bg-white/[0.03]" />
              )}
            </div>

            <div className="mt-4 flex flex-wrap items-end justify-between gap-3 border-t border-white/5 pt-4">
              <div className="min-w-0 flex-1">
                <p className="mb-2 text-[10px] uppercase tracking-[0.16em] text-slate-500">
                  What if we deploy these controls?
                </p>
                <div className="flex flex-wrap gap-2">
                  {relevantCandidates.length === 0 ? (
                    <p className="text-xs text-slate-500">
                      No investment candidate maps to this scenario.
                    </p>
                  ) : (
                    relevantCandidates.map((candidate) => (
                      <CandidateChip
                        key={candidate.id}
                        label={candidate.control_id}
                        cost={`${inrShort(candidate.cost)} · ${candidate.category}`}
                        active={selected.includes(candidate.id)}
                        onClick={() => toggleControl(candidate.id)}
                      />
                    ))
                  )}
                </div>
              </div>
              <SegmentedControl
                options={TRIAL_OPTIONS}
                value={trials}
                onChange={setTrials}
                label="Monte Carlo trial count"
              />
            </div>
          </Card>
        ) : (
          <Card>
            <p className="text-sm text-slate-400">Loading scenarios…</p>
          </Card>
        )}

        {active ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card title="Cost of delay">
              <div className="flex flex-wrap items-end gap-3">
                <label className="text-xs text-slate-400">
                  Delay remediation by
                  <input
                    type="number"
                    min={0}
                    max={3650}
                    value={delayDays}
                    aria-label="Remediation delay in days"
                    onChange={(event) => setDelayDays(Number(event.target.value))}
                    className="ml-2 w-20 rounded-md border border-white/10 bg-black/30 px-2 py-1 font-mono text-sm text-white outline-none focus:border-cyan-400/60"
                  />
                  days
                </label>
                <button
                  type="button"
                  onClick={() => delay.mutate()}
                  disabled={delay.isPending}
                  className="rounded-lg border border-cyan-400/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-medium text-cyan-200 transition hover:bg-cyan-500/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400 disabled:opacity-50"
                >
                  {delay.isPending ? "Simulating…" : "Simulate delay"}
                </button>
              </div>
              {delay.isError ? (
                <ErrorState message="The delay simulation failed." compact />
              ) : null}
              {delay.data ? (
                <div className="mt-3 space-y-1 text-xs text-slate-400">
                  <p>
                    Avoidable loss:{" "}
                    <span className="font-mono text-sm text-rose-300">
                      {inrShort(delay.data.avoidable_loss)}
                    </span>
                  </p>
                  <p className="text-[11px] leading-snug text-slate-500">{delay.data.method}</p>
                </div>
              ) : (
                <p className="mt-3 text-[11px] text-slate-500">
                  Models the annual loss rate accrued over the waiting window.
                </p>
              )}
            </Card>

            <Card title="Criticality stress test">
              <p className="text-[11px] leading-snug text-slate-500">
                Re-materializes this scenario as if the asset became business-critical across
                every dimension.
              </p>
              <button
                type="button"
                onClick={() => criticality.mutate()}
                disabled={criticality.isPending}
                className="mt-3 rounded-lg border border-fuchsia-400/40 bg-fuchsia-500/10 px-3 py-1.5 text-xs font-medium text-fuchsia-200 transition hover:bg-fuchsia-500/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fuchsia-400 disabled:opacity-50"
              >
                {criticality.isPending ? "Simulating…" : "Make it critical"}
              </button>
              {criticality.isError ? (
                <ErrorState message="The criticality stress test failed." compact />
              ) : null}
              {criticality.data ? (
                <div className="mt-3 space-y-1 text-xs text-slate-400">
                  <p>
                    Criticality {criticality.data.before.score.toFixed(2)} ({criticality.data.before.band}) →{" "}
                    <span className="text-slate-200">
                      {criticality.data.after.score.toFixed(2)} ({criticality.data.after.band})
                    </span>
                  </p>
                  <p>
                    EAL delta:{" "}
                    <span className="font-mono text-sm text-fuchsia-300">
                      +{inrShort(criticality.data.eal_delta)}
                    </span>
                  </p>
                </div>
              ) : null}
            </Card>
          </div>
        ) : null}
      </div>
    </div>
  );
}
