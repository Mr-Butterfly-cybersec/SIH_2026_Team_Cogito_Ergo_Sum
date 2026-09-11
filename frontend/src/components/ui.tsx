import type { ReactNode } from "react";

/** Shimmer block used for loading states, so panels never collapse or jump on load. */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={`animate-pulse rounded-md bg-white/[0.06] ${className}`}
    />
  );
}

export function Card({
  children,
  className = "",
  title,
  subtitle,
  action,
  id,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  id?: string;
}) {
  return (
    <section id={id} className={`glass rounded-2xl ${className}`}>
      {title ? (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-white/[0.06] px-4 py-3">
          <div className="min-w-0">
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">
              {title}
            </h2>
            {subtitle ? (
              <p className="mt-0.5 text-[11px] leading-snug text-slate-500">{subtitle}</p>
            ) : null}
          </div>
          {action}
        </header>
      ) : null}
      <div className="p-4">{children}</div>
    </section>
  );
}

/**
 * A failed request must never look like a slow one. Every panel that fetches renders this
 * instead of an endless spinner, and says what to do about it.
 */
export function ErrorState({
  message,
  onRetry,
  compact = false,
}: {
  message?: string;
  onRetry?: () => void;
  compact?: boolean;
}) {
  return (
    <div
      role="alert"
      className={`flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-rose-500/30 bg-rose-500/[0.08] px-3 py-2.5 ${
        compact ? "" : "mt-3"
      }`}
    >
      <span className="flex h-2 w-2 shrink-0 rounded-full bg-rose-400" aria-hidden />
      <span className="min-w-0 flex-1 text-[11px] leading-snug text-rose-200">
        {message ?? "Could not reach the risk engine."}
        <span className="mt-0.5 block text-rose-300/70">
          Check that the API is running, then retry.
        </span>
      </span>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-rose-400/40 bg-rose-500/10 px-2.5 py-1 text-[11px] font-medium text-rose-100 transition hover:bg-rose-500/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-400"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}

/** Consistent empty state so a zero-result panel reads as intentional, not broken. */
export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-xl border border-dashed border-white/10 px-3 py-6 text-center text-[11px] text-slate-500">
      {children}
    </p>
  );
}

export function Stat({
  label,
  value,
  sub,
  tone = "default",
  hint,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "default" | "accent" | "danger" | "muted";
  hint?: string;
}) {
  const color =
    tone === "accent"
      ? "text-cyan-300"
      : tone === "danger"
        ? "text-rose-300"
        : tone === "muted"
          ? "text-slate-400"
          : "text-white";
  return (
    <div className="min-w-0" title={hint}>
      <p className="truncate text-[10px] uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className={`mt-1 truncate text-xl font-semibold tabular-nums ${color}`}>{value}</p>
      {sub ? <p className="mt-0.5 truncate text-[11px] text-slate-500">{sub}</p> : null}
    </div>
  );
}

export function Badge({
  children,
  className = "",
  title,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${className}`}
    >
      {children}
    </span>
  );
}

export function CandidateChip({
  label,
  active,
  onClick,
  cost,
  title,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  cost: string;
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      title={title}
      className={`hover-lift rounded-lg border px-2.5 py-1.5 text-left text-[11px] transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400 ${
        active
          ? "border-cyan-400/60 bg-cyan-500/15 text-cyan-100"
          : "border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/25 hover:text-white"
      }`}
    >
      <span className="block font-medium leading-tight">{label}</span>
      <span className="mt-0.5 block font-mono text-[10px] text-slate-500">{cost}</span>
    </button>
  );
}

/** Small segmented control; used for the trial-count selector and similar toggles. */
export function SegmentedControl<T extends string | number>({
  options,
  value,
  onChange,
  label,
}: {
  options: { label: string; value: T; hint?: string }[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className="flex items-center gap-0.5 rounded-lg border border-white/10 p-0.5"
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={String(option.value)}
            type="button"
            onClick={() => onChange(option.value)}
            aria-pressed={active}
            title={option.hint}
            className={`rounded-md px-2 py-1 text-[10px] uppercase tracking-wider transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-cyan-400 ${
              active ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

/** Horizontal labelled bar — the visual language for "exposure share" across the dashboard. */
export function ShareBar({
  value,
  max,
  tone = "neutral",
  animate = true,
}: {
  value: number;
  max: number;
  tone?: "neutral" | "active";
  animate?: boolean;
}) {
  const width = max > 0 ? Math.max((value / max) * 100, 1.5) : 0;
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
      {/* The bar grows from the left so the reader watches the magnitude being drawn,
          rather than having to compare two static widths. */}
      <div
        className={`h-full rounded-full ${
          tone === "active"
            ? "bg-gradient-to-r from-emerald-400 to-cyan-400"
            : "bg-slate-500/70"
        } ${animate ? "animate-grow" : ""}`}
        style={{ width: `${Math.min(width, 100)}%` }}
      />
    </div>
  );
}
