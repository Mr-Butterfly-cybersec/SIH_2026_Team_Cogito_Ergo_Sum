"use client";

import { useQuery } from "@tanstack/react-query";

import { Badge, Card, ErrorState, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { CONFIDENCE_COLOR, pct } from "@/lib/format";

const SOURCE_META: Record<string, { label: string; className: string; note: string }> = {
  PUBLIC_DATA: {
    label: "Public data",
    className: "bg-emerald-500/60",
    note: "NVD, EPSS, KEV, ATT&CK — dated and citable",
  },
  OBSERVED_TELEMETRY: {
    label: "Observed telemetry",
    className: "bg-cyan-500/60",
    note: "measured from our own estate",
  },
  USER_INPUT: {
    label: "Your input",
    className: "bg-sky-500/60",
    note: "supplied by the analyst",
  },
  MODEL_ESTIMATE: {
    label: "Model estimate",
    className: "bg-amber-500/60",
    note: "inferred by the model, not measured",
  },
  SYNTHETIC_DEMO: {
    label: "Synthetic (demo)",
    className: "bg-rose-500/60",
    note: "invented for the demonstration — never presented as fact",
  },
};

const SOURCE_ORDER = [
  "PUBLIC_DATA",
  "OBSERVED_TELEMETRY",
  "USER_INPUT",
  "MODEL_ESTIMATE",
  "SYNTHETIC_DEMO",
];

const ASSUMPTIONS = [
  "Losses are modelled per year from a seeded Monte Carlo run — the same seed reproduces the same numbers.",
  "Control effectiveness combines as 1 − Π(1 − eᵢ), which assumes controls fail independently. A first-order approximation: real controls share blind spots.",
  "Risk reduction is submodular — overlapping controls deliver diminishing returns, so portfolio results are re-simulated rather than summed.",
  "Absence from CISA KEV means not-yet-confirmed-exploited, not safe. A missing EPSS score is unknown, not zero.",
  "CVSS severity is not financial risk. This platform ranks by modelled rupee exposure, not by score.",
  "No number originates in the language model. It selects an engine tool and explains the result — it may round and convert units for readability, but every figure traces back to the engine.",
];

export function DataConfidencePanel() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.overview });

  if (overview.isError) {
    return (
      <Card title="Data confidence & assumptions">
        <ErrorState
          message="Could not load the evidence mix."
          onRetry={() => overview.refetch()}
          compact
        />
      </Card>
    );
  }

  if (!overview.data) {
    return (
      <Card title="Data confidence & assumptions">
        <Skeleton className="h-2.5 w-full rounded-full" />
        <div className="mt-3 grid gap-1.5 sm:grid-cols-2">
          {[0, 1, 2, 3].map((row) => (
            <Skeleton key={row} className="h-6 w-full" />
          ))}
        </div>
      </Card>
    );
  }

  const { evidence_mix: mix, posture, model_version } = overview.data;
  const sources = SOURCE_ORDER.filter((key) => (mix.proportions[key] ?? 0) > 0);
  const unknown = Object.keys(mix.proportions).filter(
    (key) => !SOURCE_ORDER.includes(key) && (mix.proportions[key] ?? 0) > 0,
  );

  return (
    <Card
      title="Data confidence & assumptions"
      action={
        <Badge className={CONFIDENCE_COLOR[mix.band] ?? "border-white/15 text-slate-400"}>
          {mix.band} · {pct(mix.confidence_score * 100, 0)}
        </Badge>
      }
    >
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-white/5">
        {[...sources, ...unknown].map((key) => (
          <div
            key={key}
            className={SOURCE_META[key]?.className ?? "bg-slate-500/60"}
            style={{ width: `${(mix.proportions[key] ?? 0) * 100}%` }}
            title={`${SOURCE_META[key]?.label ?? key} — ${pct((mix.proportions[key] ?? 0) * 100, 1)}`}
          />
        ))}
      </div>

      <ul className="mt-3 grid gap-1.5 sm:grid-cols-2">
        {[...sources, ...unknown].map((key) => {
          const meta = SOURCE_META[key];
          const proportion = mix.proportions[key] ?? 0;
          const count = mix.counts[key];
          return (
            <li key={key} className="flex items-start gap-2 text-[11px] leading-snug">
              <span
                className={`mt-1 h-2 w-2 shrink-0 rounded-full ${meta?.className ?? "bg-slate-500/60"}`}
              />
              <span className="min-w-0">
                <span className="font-medium text-slate-300">
                  {meta?.label ?? key} · {pct(proportion * 100, 0)}
                  {typeof count === "number" ? (
                    <span className="text-slate-500"> ({count.toLocaleString("en-IN")})</span>
                  ) : null}
                </span>
                {meta?.note ? (
                  <span className="block text-slate-500">{meta.note}</span>
                ) : null}
              </span>
            </li>
          );
        })}
      </ul>

      <div className="mt-4 border-t border-white/5 pt-3">
        <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
          Assumptions this result depends on
        </p>
        <ul className="mt-2 space-y-1.5">
          {ASSUMPTIONS.map((item) => (
            <li key={item} className="flex gap-2 text-[11px] leading-snug text-slate-400">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-600" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-3 border-t border-white/5 pt-3 font-mono text-[10px] text-slate-600">
        model v{model_version} · {posture.n_trials.toLocaleString("en-IN")} trials · seed{" "}
        {posture.seed} · {posture.n_scenarios} scenarios
      </p>
    </Card>
  );
}
