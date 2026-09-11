"use client";

import { useQuery } from "@tanstack/react-query";

import { Badge, ErrorState, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { BAND_COLOR, CONFIDENCE_COLOR, inrShort, pct } from "@/lib/format";
import { useCountUp } from "@/lib/useCountUp";

const BAND_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

/**
 * The decision, in one block, before any of the evidence.
 *
 * The dashboard previously opened with a numeric strip alone. Numbers without a "so what"
 * leave a reader to work out why they matter — so this states the exposure, **names the
 * single largest risk**, and offers the two actions a decision-maker would take next.
 * Everything below it is the evidence for these sentences.
 */
export function ExecutiveBriefing() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.overview });
  const scenarios = useQuery({ queryKey: ["scenarios"], queryFn: api.scenarios });

  // Hooks run before any early return so the call order is stable across renders. Zeros are
  // animated too — the count-up starts from 0 and settles on the true value once loaded.
  const postureEal = overview.data?.posture.baseline_eal ?? 0;
  const postureP90 = overview.data?.posture.p90 ?? 0;
  const postureP95 = overview.data?.posture.p95 ?? 0;
  const animatedEal = useCountUp(postureEal, 800);
  const animatedP90 = useCountUp(postureP90, 900);
  const animatedP95 = useCountUp(postureP95, 1000);

  if (overview.isError) {
    return (
      <section className="glass rounded-2xl p-4">
        <ErrorState
          message="Could not load the organization's risk posture."
          onRetry={() => overview.refetch()}
          compact
        />
      </section>
    );
  }

  if (!overview.data) {
    return (
      <section className="glass rounded-2xl p-4">
        <div className="space-y-3">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/4" />
        </div>
      </section>
    );
  }

  const { counts, criticality_bands: bands, evidence_mix: mix, model_version } = overview.data;

  // Defensive sort: the API ranks by exposure, but the headline claim should not depend on
  // someone else's ordering.
  const top = [...(scenarios.data ?? [])].sort(
    (a, b) => (b.baseline_eal ?? 0) - (a.baseline_eal ?? 0),
  )[0];

  return (
    <section className="glass overflow-hidden rounded-2xl">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.06] px-4 py-2.5">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">
          Executive briefing
        </h2>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge
            className={CONFIDENCE_COLOR[mix.band] ?? "border-white/15 text-slate-400"}
            title={`${pct(mix.confidence_score * 100, 1)} credibility-weighted across ${mix.counts ? Object.values(mix.counts).reduce((a, b) => a + b, 0) : 0} inputs`}
          >
            {mix.band} confidence · {pct(mix.confidence_score * 100, 0)}
          </Badge>
          <Badge className="border-white/15 bg-white/5 text-slate-400">model v{model_version}</Badge>
        </div>
      </div>

      <div className="p-4">
        <div className="flex flex-wrap items-end gap-x-8 gap-y-4">
          <div className="animate-rise">
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
              Expected annual loss
            </p>
            <p className="mt-1 text-3xl font-semibold tabular-nums text-cyan-300 sm:text-4xl">
              {inrShort(animatedEal)}
            </p>
          </div>
          <div className="animate-rise [animation-delay:80ms]">
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
              P95 · 1-in-20 year
            </p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-white">
              {inrShort(animatedP95)}
            </p>
          </div>
          <div className="animate-rise [animation-delay:160ms]">
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
              1-in-10 year
            </p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-white">
              {inrShort(animatedP90)}
            </p>
          </div>
        </div>

        {/* The single most useful sentence on the page: what to worry about first. */}
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-300">
          {top ? (
            <>
              The largest single exposure is{" "}
              <span className="font-medium text-white">{top.name}</span>
              {top.asset_name ? <> on {top.asset_name}</> : null} —{" "}
              <span className="font-medium text-cyan-200">
                {inrShort(top.baseline_eal ?? 0)}
              </span>{" "}
              a year
              {top.max_cvss !== null ? <> at CVSS {top.max_cvss.toFixed(1)}</> : null}
              {top.max_epss !== null ? <> and {(top.max_epss * 100).toFixed(1)}% EPSS</> : null}.
            </>
          ) : (
            <>No scenarios are modelled for this organization yet.</>
          )}{" "}
          <span className="text-slate-500">
            Every figure is a modelled distribution, not an accounting fact.
          </span>
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <a
            href="#optimizer"
            className="rounded-xl border border-emerald-400/50 bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 px-4 py-2 text-[13px] font-semibold text-emerald-100 transition hover:from-emerald-500/30 hover:to-cyan-500/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
          >
            Where should the budget go? →
          </a>
          <a
            href="#ask"
            className="rounded-xl border border-white/15 px-4 py-2 text-[13px] font-medium text-slate-300 transition hover:border-white/30 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400"
          >
            Ask the engine
          </a>
          <a
            href="#confidence"
            className="rounded-xl px-3 py-2 text-[13px] text-slate-500 transition hover:text-slate-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400"
          >
            What is this based on?
          </a>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/[0.06] pt-3">
          <div className="flex items-center gap-1.5">
            {BAND_ORDER.map((band) =>
              bands[band] ? (
                <Badge key={band} className={BAND_COLOR[band]}>
                  {bands[band]} {band}
                </Badge>
              ) : null,
            )}
          </div>
          <p className="text-[11px] text-slate-500">
            {counts.assets} assets · {counts.services} services · {counts.findings} findings ·{" "}
            {counts.controls} controls · {counts.vulnerabilities_enriched} CVEs enriched
          </p>
        </div>
      </div>
    </section>
  );
}
