"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function HealthBadge() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 15_000,
  });

  const state = isLoading ? "connecting" : isError ? "offline" : "online";
  const dot =
    state === "online"
      ? "bg-emerald-400"
      : state === "offline"
        ? "bg-rose-500"
        : "bg-amber-400";

  return (
    <div className="glass flex items-center gap-3 rounded-full px-4 py-2 text-sm">
      <span className="relative flex h-2.5 w-2.5">
        <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
      </span>
      <span className="text-slate-300">
        API {state}
        {data ? (
          <span className="ml-2 font-mono text-slate-500">v{data.version}</span>
        ) : null}
      </span>
    </div>
  );
}
