"""Run the benchmark and write the proof artifacts.

uv run python -m app.optimization.benchmark [--trials N] [--stamp]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.engine.service import get_engine
from app.optimization.benchmark import (
    DEFAULT_BUDGETS,
    DEFAULT_SEEDS,
    DEFAULT_TRIALS,
    render_markdown,
    run_benchmark,
    write_json,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark the optimizer against baselines.")
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--exact", action="store_true", default=True)
    parser.add_argument("--no-exact", dest="exact", action="store_false")
    args = parser.parse_args(argv)

    print(
        f"Running benchmark · trials {args.trials} · "
        f"budgets {len(DEFAULT_BUDGETS)} · seeds {len(DEFAULT_SEEDS)}"
    )
    report = run_benchmark(
        get_engine(),
        budgets=DEFAULT_BUDGETS,
        seeds=DEFAULT_SEEDS,
        n_trials=args.trials,
        exact=args.exact,
    )

    markdown_path = DOCS / "benchmark.md"
    json_path = DOCS / "benchmark.json"
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    write_json(report, json_path)

    gaps = [
        r.optimizer_vs_cvss_points for r in report.results if r.optimizer_vs_cvss_points is not None
    ]
    if gaps:
        print(
            f"optimizer vs CVSS-first: min {min(gaps):+.2f} · max {max(gaps):+.2f} · "
            f"mean {sum(gaps) / len(gaps):+.2f} percentage points"
        )
    optimum_gaps = [r.optimizer_gap_to_optimum_points for r in report.results if r.exact_optimum]
    if optimum_gaps:
        print(f"worst gap to exact optimum: {max(optimum_gaps):.2f} percentage points")

    print(f"wrote {markdown_path.relative_to(REPO_ROOT)}")
    print(f"wrote {json_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
