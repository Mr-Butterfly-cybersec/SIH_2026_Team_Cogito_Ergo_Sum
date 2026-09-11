"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Card, ErrorState, Skeleton, Stat } from "@/components/ui";
import { api } from "@/lib/api";
import { decimal, inrShort, pct } from "@/lib/format";
import type { CoverageStatus } from "@/types/api";

const STATUS_STYLE: Record<CoverageStatus, string> = {
  COVERED: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  PARTIAL: "border-yellow-500/40 bg-yellow-500/10 text-yellow-300",
  GAP: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  NOT_APPLICABLE: "border-white/15 bg-white/5 text-slate-400",
};

function barColor(coverage: number): string {
  if (coverage >= 0.7) return "bg-gradient-to-r from-emerald-400 to-cyan-400";
  if (coverage >= 0.35) return "bg-gradient-to-r from-yellow-400 to-orange-400";
  return "bg-gradient-to-r from-rose-500 to-rose-400";
}

export function CompliancePanel() {
  const [frameworkId, setFrameworkId] = useState<string | null>(null);
  const report = useQuery({ queryKey: ["compliance"], queryFn: () => api.compliance() });

  if (report.isLoading) {
    return (
      <Card title="Framework alignment">
        <div className="space-y-3">
          <Skeleton className="h-9 w-full rounded-lg" />
          <Skeleton className="h-[120px] w-full rounded-xl" />
        </div>
      </Card>
    );
  }
  if (report.isError || !report.data) {
    return (
      <Card title="Framework alignment">
        <ErrorState
          message="Could not load framework coverage."
          onRetry={() => report.refetch()}
          compact
        />
      </Card>
    );
  }

  const data = report.data;
  const active = data.frameworks.find((f) => f.framework.id === frameworkId) ?? data.frameworks[0];

  return (
    <Card
      title="Framework alignment"
      action={
        <Badge className="border-white/15 bg-white/5 text-slate-400">
          catalog {data.catalog_version}
        </Badge>
      }
    >
      <p className="mb-4 text-[11px] leading-snug text-slate-500">
        One internal control ontology mapped to seven frameworks. Coverage comes from the
        measured effectiveness of your real controls — and each gap is priced at the modelled
        annual loss it relates to, so it can compete for budget like any other risk.
      </p>

      <div className="grid grid-cols-2 gap-4 border-y border-white/5 py-4 sm:grid-cols-4">
        <Stat
          label="Overall coverage"
          value={pct(data.overall_coverage * 100)}
          sub={`${active?.counts.requirements ?? 0} requirements tracked`}
          tone="accent"
        />
        <Stat
          label="Covered"
          value={String(active?.counts.covered ?? 0)}
          sub="meeting threshold"
        />
        <Stat label="Partial" value={String(active?.counts.partial ?? 0)} sub="weak control" />
        <Stat
          label="Gaps"
          value={String(active?.counts.gaps ?? 0)}
          sub={`${inrShort(active?.gap_exposure ?? 0)} exposed`}
          tone="danger"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {data.frameworks.map((entry) => {
          const isActive = entry.framework.id === active?.framework.id;
          return (
            <button
              key={entry.framework.id}
              type="button"
              onClick={() => setFrameworkId(entry.framework.id)}
              className={`rounded-lg border px-3 py-2 text-left transition ${
                isActive
                  ? "border-cyan-400/50 bg-cyan-500/10"
                  : "border-white/10 bg-white/[0.03] hover:border-white/25"
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`text-[11px] font-medium ${
                    isActive ? "text-cyan-100" : "text-slate-300"
                  }`}
                >
                  {entry.framework.short_name}
                </span>
                {entry.framework.kind === "regulation" ? (
                  <Badge className="border-fuchsia-500/40 bg-fuchsia-500/10 text-fuchsia-300">
                    India
                  </Badge>
                ) : null}
              </div>
              <div className="mt-1.5 flex items-center gap-2">
                <div className="h-1 w-20 overflow-hidden rounded-full bg-white/5">
                  <div
                    className={`h-full rounded-full ${barColor(entry.coverage)}`}
                    style={{ width: `${Math.max(entry.coverage * 100, 3)}%` }}
                  />
                </div>
                <span className="font-mono text-[10px] text-slate-400">
                  {pct(entry.coverage * 100)}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {active ? (
        <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,300px)_minmax(0,1fr)]">
          <div className="min-w-0">
            <p className="mb-2 text-[10px] uppercase tracking-[0.16em] text-slate-500">
              By security function
            </p>
            <ul className="space-y-2">
              {active.functions.map((fn) => (
                <li key={fn.function} className="flex items-center gap-3">
                  <span className="w-24 shrink-0 text-[11px] text-slate-300">{fn.function}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                    <div
                      className={`h-full rounded-full ${barColor(fn.coverage)}`}
                      style={{ width: `${Math.max(fn.coverage * 100, 2)}%` }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right font-mono text-[10px] text-slate-400">
                    {Math.round(fn.coverage * 100)}%
                  </span>
                  {fn.gaps > 0 ? (
                    <span className="w-14 shrink-0 text-right font-mono text-[10px] text-rose-400">
                      {fn.gaps} gap{fn.gaps > 1 ? "s" : ""}
                    </span>
                  ) : (
                    <span className="w-14 shrink-0" />
                  )}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-[10px] leading-snug text-slate-600">
              {active.framework.name} · {active.framework.publisher} · v
              {active.framework.version}
            </p>
          </div>

          <div className="min-w-0">
            <p className="mb-2 text-[10px] uppercase tracking-[0.16em] text-slate-500">
              Gaps and partial coverage, ranked by rupee exposure
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[11px]">
                <thead className="text-slate-500">
                  <tr className="border-b border-white/5">
                    <th className="py-1.5 font-medium">Requirement</th>
                    <th className="py-1.5 font-medium">Cited</th>
                    <th className="py-1.5 text-right font-medium">Coverage</th>
                    <th className="py-1.5 text-right font-medium">Exposure</th>
                    <th className="py-1.5 text-right font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="text-slate-300">
                  {active.requirements
                    .filter((r) => r.status !== "COVERED")
                    .sort((a, b) => b.exposure - a.exposure)
                    .slice(0, 8)
                    .map((row) => (
                      <tr key={row.id} className="border-b border-white/[0.04] align-top">
                        <td className="py-1.5 pr-2">
                          <span className="block text-slate-200">{row.name}</span>
                          <span className="block font-mono text-[10px] text-slate-600">
                            {row.id}
                          </span>
                        </td>
                        <td className="py-1.5 pr-2 font-mono text-[10px] text-slate-500">
                          {row.references.slice(0, 2).join(", ")}
                        </td>
                        <td className="py-1.5 text-right font-mono">
                          {decimal(row.coverage, 2)}
                        </td>
                        <td className="py-1.5 text-right font-mono text-slate-200">
                          {row.exposure > 0 ? inrShort(row.exposure) : "—"}
                        </td>
                        <td className="py-1.5 text-right">
                          <Badge className={STATUS_STYLE[row.status]}>{row.status}</Badge>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}

      {data.unmapped_requirements.length > 0 ? (
        <p className="mt-4 border-t border-white/5 pt-3 text-[10px] leading-snug text-slate-500">
          <span className="text-slate-400">
            {data.unmapped_requirements.length} requirements have no control mapped at all
          </span>{" "}
          (e.g. adversarial testing, security awareness, supplier risk) — organizational
          controls the estate has not implemented. They appear as gaps with no technical
          control to close them.
        </p>
      ) : null}
    </Card>
  );
}
