"""Run the example scenario end to end and print a summary.

uv run python -m app.risk.demo
"""

from __future__ import annotations

from pathlib import Path

from app.risk.schemas import load_scenario, simulate

EXAMPLE = Path(__file__).parent / "examples" / "ransomware.json"


def _inr(value: float) -> str:
    return f"₹{value:,.0f}"


def main() -> None:
    scenario = load_scenario(EXAMPLE)
    result = simulate(scenario, n_trials=100_000, seed=42)
    s = result.summary

    print(f"\n{scenario.name}  [{scenario.id}]")
    print(f"asset: {scenario.asset_id}   service: {scenario.business_service}")
    print("-" * 62)
    print(f"  EAL        {_inr(s.eal):>18}")
    print(f"  P50        {_inr(s.p50):>18}")
    print(f"  P90        {_inr(s.p90):>18}")
    print(f"  P95 (VaR)  {_inr(s.p95):>18}")
    print(f"  P99        {_inr(s.p99):>18}")
    print(f"  CVaR 95    {_inr(s.cvar_95):>18}")
    print("-" * 62)
    print(f"  mean TEF   {result.mean_tef:>18.3f}  events/yr")
    print(f"  vulnerability {result.vulnerability:>14.4f}")
    print(f"  mean LEF   {result.mean_lef:>18.3f}  losses/yr")
    print("-" * 62)
    mix = result.evidence_mix
    print(f"  evidence confidence  {mix.confidence_score:.2f}  ({mix.band.value})")
    for source, share in sorted(mix.proportions.items(), key=lambda kv: -kv[1]):
        print(f"    {source:<22} {share * 100:5.1f}%")
    print(
        f"\n  reproducible: seed={result.seed} n={result.n_trials} model={result.model_version}\n"
    )


if __name__ == "__main__":
    main()
