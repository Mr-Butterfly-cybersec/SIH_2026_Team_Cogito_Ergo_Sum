"use client";

import type { EChartsOption } from "echarts";
import { useMemo } from "react";

import { Chart } from "@/components/charts/Chart";
import { inrShort } from "@/lib/format";
import type { Histogram, LossSummary } from "@/types/api";

const MARKER_COLORS = { eal: "#38bdf8", p90: "#fb923c", p95: "#f43f5e" };

function markerLines(
  values: { value: number; label: string; color: string }[],
  indexOf: (value: number) => string | number,
) {
  return {
    symbol: "none",
    silent: true,
    label: {
      formatter: (p: unknown) => (p as { name: string }).name,
      position: "insideEndTop" as const,
      color: "rgba(226,232,240,0.85)",
      fontSize: 10,
    },
    lineStyle: { width: 1.5, type: "dashed" as const },
    data: values.map((item) => ({
      name: `${item.label} ${inrShort(item.value)}`,
      xAxis: indexOf(item.value),
      lineStyle: { color: item.color },
    })),
  };
}

/** Annual-loss histogram with the headline percentiles marked on top. */
export function LossHistogram({
  histogram,
  summary,
  height = 220,
}: {
  histogram: Histogram;
  summary: LossSummary;
  height?: number;
}) {
  const option = useMemo<EChartsOption>(() => {
    const midpoints = histogram.bins.slice(0, -1).map((edge, i) => (edge + histogram.bins[i + 1]) / 2);
    const labels = midpoints.map((value) => inrShort(value));

    const nearestLabel = (value: number) => {
      let best = 0;
      let bestDistance = Infinity;
      midpoints.forEach((midpoint, index) => {
        const distance = Math.abs(midpoint - value);
        if (distance < bestDistance) {
          bestDistance = distance;
          best = index;
        }
      });
      return labels[best];
    };

    return {
      grid: { left: 44, right: 12, top: 28, bottom: 30 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(6,10,20,0.92)",
        borderColor: "rgba(255,255,255,0.12)",
        textStyle: { color: "#e2e8f0", fontSize: 11 },
        formatter: (params: unknown) => {
          const first = (params as { dataIndex: number; name: string }[])[0];
          const count = histogram.counts[first.dataIndex];
          const total = histogram.counts.reduce((a, b) => a + b, 0);
          return `Loss ≈ ${first.name}<br/>${count.toLocaleString("en-IN")} trials (${((count / total) * 100).toFixed(1)}%)`;
        },
      },
      xAxis: {
        type: "category",
        data: labels,
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.15)" } },
        axisLabel: { color: "rgba(226,232,240,0.6)", fontSize: 9, interval: 9, rotate: 0 },
      },
      yAxis: {
        type: "value",
        name: "trials",
        nameTextStyle: { color: "rgba(226,232,240,0.5)", fontSize: 10 },
        axisLabel: { color: "rgba(226,232,240,0.6)", fontSize: 10 },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      },
      series: [
        {
          type: "bar",
          data: histogram.counts,
          itemStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(56,189,248,0.85)" },
                { offset: 1, color: "rgba(56,189,248,0.12)" },
              ],
            },
            borderRadius: [2, 2, 0, 0],
          },
          markLine: markerLines(
            [
              { value: summary.eal, label: "EAL", color: MARKER_COLORS.eal },
              { value: summary.p90, label: "P90", color: MARKER_COLORS.p90 },
              { value: summary.p95, label: "P95", color: MARKER_COLORS.p95 },
            ],
            nearestLabel,
          ),
        },
      ],
    };
  }, [histogram, summary]);

  return <Chart option={option} height={height} />;
}

/** Loss-exceedance curve: P(annual loss > x). The decision-relevant view. */
export function LossExceedance({
  lossExceedance,
  summary,
  height = 220,
}: {
  lossExceedance: { loss: number[]; probability: number[] };
  summary: LossSummary;
  height?: number;
}) {
  const option = useMemo<EChartsOption>(() => {
    const points = lossExceedance.loss.map((loss, index) => [
      loss,
      lossExceedance.probability[index],
    ]);

    return {
      grid: { left: 52, right: 16, top: 28, bottom: 32 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(6,10,20,0.92)",
        borderColor: "rgba(255,255,255,0.12)",
        textStyle: { color: "#e2e8f0", fontSize: 11 },
        formatter: (params: unknown) => {
          const point = (params as { value: [number, number] }[])[0].value;
          return `Loss ${inrShort(point[0])}<br/>P(loss > x) = ${(point[1] * 100).toFixed(1)}%`;
        },
      },
      xAxis: {
        type: "value",
        axisLabel: {
          color: "rgba(226,232,240,0.6)",
          fontSize: 10,
          formatter: (value: number) => inrShort(value),
        },
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.15)" } },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      },
      yAxis: {
        type: "value",
        name: "P(loss > x)",
        max: 1,
        nameTextStyle: { color: "rgba(226,232,240,0.5)", fontSize: 10 },
        axisLabel: {
          color: "rgba(226,232,240,0.6)",
          fontSize: 10,
          formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
        },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      },
      series: [
        {
          type: "line",
          data: points,
          showSymbol: false,
          smooth: true,
          lineStyle: { width: 2, color: "#38bdf8" },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(56,189,248,0.35)" },
                { offset: 1, color: "rgba(56,189,248,0.02)" },
              ],
            },
          },
          markLine: {
            symbol: "none",
            silent: true,
            label: {
              formatter: (p: unknown) => (p as { name: string }).name,
              position: "insideEndTop" as const,
              color: "rgba(226,232,240,0.85)",
              fontSize: 10,
            },
            lineStyle: { width: 1.5, type: "dashed" as const },
            data: [
              { name: `P90 ${inrShort(summary.p90)}`, xAxis: summary.p90, lineStyle: { color: MARKER_COLORS.p90 } },
              { name: `P95 ${inrShort(summary.p95)}`, xAxis: summary.p95, lineStyle: { color: MARKER_COLORS.p95 } },
            ],
          },
        },
      ],
    };
  }, [lossExceedance, summary]);

  return <Chart option={option} height={height} />;
}
