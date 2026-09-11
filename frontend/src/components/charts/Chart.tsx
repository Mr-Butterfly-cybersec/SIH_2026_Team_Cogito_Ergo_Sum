"use client";

import * as echarts from "echarts";
import type { EChartsOption } from "echarts";
import { useEffect, useRef } from "react";

interface ChartProps {
  option: EChartsOption;
  height?: number;
  className?: string;
}

/**
 * Minimal ECharts host driven directly through the core API.
 *
 * `echarts-for-react` is avoided deliberately: it depends on APIs React 19 removed.
 * Init happens in an effect, so nothing touches the DOM during server rendering.
 */
export function Chart({ option, height = 240, className }: ChartProps) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!container.current) return;
    const chart = echarts.init(container.current, undefined, { renderer: "canvas" });
    instance.current = chart;

    // Window resize alone is not enough: these charts sit in a grid that reflows when the
    // scenario list is toggled or a panel changes width, and ECharts will render at the old
    // size until something tells it otherwise. Observing the container catches both.
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(container.current);

    return () => {
      observer.disconnect();
      chart.dispose();
      instance.current = null;
    };
  }, []);

  useEffect(() => {
    instance.current?.setOption(option, true);
  }, [option]);

  return <div ref={container} style={{ height, width: "100%" }} className={className} />;
}

export const AXIS_STYLE = {
  axisLine: { lineStyle: { color: "rgba(255,255,255,0.15)" } },
  axisLabel: { color: "rgba(226,232,240,0.65)", fontSize: 10 },
  splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
};
