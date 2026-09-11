import { AskPanel } from "@/components/AskPanel";
import { CompliancePanel } from "@/components/CompliancePanel";
import { DataConfidencePanel } from "@/components/DataConfidencePanel";
import { ExecutiveBriefing } from "@/components/ExecutiveBriefing";
import { HealthBadge } from "@/components/HealthBadge";
import { OptimizerPanel } from "@/components/OptimizerPanel";
import { ScenarioExplorer } from "@/components/ScenarioExplorer";
import { SectionNav } from "@/components/SectionNav";

/** The sticky nav is ~44px tall, so anchors need at least that much clearance. */
const SECTION = "scroll-mt-16";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-[1500px] flex-col gap-4 px-4 py-6 sm:px-6 sm:py-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-cyan-400">
            SIH26105 · Cyber Risk Decision Engine
          </p>
          <h1 className="mt-1.5 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            From CVE to ₹ impact to optimal security spend
          </h1>
          <p className="mt-1 max-w-2xl text-sm leading-snug text-slate-400">
            Every figure is modelled from real public intelligence plus declared assumptions. No
            number originates in the language model — it selects an engine tool and explains the
            result.
          </p>
        </div>
        <HealthBadge />
      </header>

      <SectionNav />

      <div id="briefing" className={SECTION}>
        <ExecutiveBriefing />
      </div>

      <div id="scenarios" className={SECTION}>
        <ScenarioExplorer />
      </div>

      <div id="optimizer" className={SECTION}>
        <OptimizerPanel />
      </div>

      <div id="compliance" className={SECTION}>
        <CompliancePanel />
      </div>

      <div id="ask" className={SECTION}>
        <AskPanel />
      </div>

      <div id="confidence" className={SECTION}>
        <DataConfidencePanel />
      </div>

      <footer className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.06] pt-4 text-[11px] text-slate-600">
        <span>
          Deterministic core · seeded Monte Carlo · provenance on every parameter · no number
          originates in the LLM
        </span>
        <span className="font-mono">
          NIST CSF 2.0 · CIS v8.1 · ISO 27001 · ISO 42001 · RBI · SEBI · DPDP
        </span>
      </footer>
    </main>
  );
}
