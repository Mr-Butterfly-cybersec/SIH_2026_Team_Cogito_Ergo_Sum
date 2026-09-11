"use client";

import type { EChartsOption } from "echarts";
import { useMemo } from "react";

import { Chart } from "@/components/charts/Chart";
import { inrShort } from "@/lib/format";
import type { PortfolioOutcome } from "@/types/api";

const STRATEGY_LABELS: Record<string, string> = {
  "current posture": "Nothing (do nothing)",
  optimizer: "Our optimizer (CP-SAT)",
  cvss_first: "Highest-CVSS first",
  epss_first: "Highest-EPSS first",
  density_greedy: "Risk-reduction per ₹",
  cheapest_first: "Cheapest first",
};

export function strategyLabel(label: string): string {
  return STRATEGY_LABELS[label] ?? label;
}

/** Re-simulated risk reduction per strategy — the optimizer vs the naive baselines. */
export function StrategyBars({
  outcomes,
  height = 260,
}: {
  outcomes: PortfolioOutcome[];
  height?: number;
}) {
  const ranked = useMemo(
    () => [...outcomes].sort((a, b) => (a.risk_reduction_pct ?? 0) - (b.risk_reduction_pct ?? 0)),
    [outcomes],
  );

  const axisMax = useMemo(() => {
    const peak = Math.max(0, ...ranked.map((row) => row.risk_reduction_pct ?? 0));
    return Math.min(100, Math.max(10, Math.ceil((peak * 1.2) / 5) * 5));
  }, [ranked]);

  const option = useMemo<EChartsOption>(
    () => ({
      grid: { left: 148, right: 60, top: 8, bottom: 24 },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "rgba(6,10,20,0.92)",
        borderColor: "rgba(255,255,255,0.12)",
        textStyle: { color: "#e2e8f0", fontSize: 11 },
        formatter: (params: unknown) => {
          const index = (params as { dataIndex: number }[])[0].dataIndex;
          const row = ranked[index];
          return [
            `<b>${strategyLabel(row.label)}</b>`,
            `Risk removed: ${(row.risk_reduction_pct ?? 0).toFixed(1)}% (${inrShort(row.risk_reduction)})`,
            `Spend: ${inrShort(row.spend)}`,
            `EAL after: ${inrShort(row.eal)}`,
            `Controls: ${row.selection.length}`,
          ].join("<br/>");
        },
      },
      xAxis: {
        type: "value",
        max: axisMax,
        axisLabel: {
          color: "rgba(226,232,240,0.6)",
          fontSize: 10,
          formatter: (value: number) => `${value}%`,
        },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      },
      yAxis: {
        type: "category",
        data: ranked.map((row) => strategyLabel(row.label)),
        axisLabel: { color: "rgba(226,232,240,0.8)", fontSize: 11 },
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.15)" } },
      },
      series: [
        {
          type: "bar",
          data: ranked.map((row) => ({
            value: Number((row.risk_reduction_pct ?? 0).toFixed(2)),
            itemStyle: {
              borderRadius: [0, 4, 4, 0],
              color:
                row.label === "optimizer"
                  ? {
                      type: "linear",
                      x: 0,
                      y: 0,
                      x2: 1,
                      y2: 0,
                      colorStops: [
                        { offset: 0, color: "#10b981" },
                        { offset: 1, color: "#06b6d4" },
                      ],
                    }
                  : "rgba(148,163,184,0.45)",
            },
          })),
          label: {
            show: true,
            position: "right",
            color: "rgba(226,232,240,0.9)",
            fontSize: 11,
            formatter: (p: unknown) => `${Number((p as { value: number }).value).toFixed(1)}%`,
          },
          barWidth: "58%",
        },
      ],
    }),
    [ranked, axisMax],
  );

  return <Chart option={option} height={height} />;
}
