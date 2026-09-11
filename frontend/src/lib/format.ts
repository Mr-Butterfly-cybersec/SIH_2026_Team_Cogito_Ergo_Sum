const CRORE = 10_000_000;
const LAKH = 100_000;

/** Full rupee figure with Indian digit grouping, e.g. ₹56,48,063. */
export function inr(value: number, fractionDigits = 0): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(value);
}

/** Indian short scale, e.g. ₹5.65 Cr, ₹56.5 L, ₹9,500. */
export function inrShort(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= CRORE) return `${sign}₹${(abs / CRORE).toFixed(2)} Cr`;
  if (abs >= LAKH) return `${sign}₹${(abs / LAKH).toFixed(1)} L`;
  if (abs >= 1_000) return `${sign}₹${(abs / 1_000).toFixed(1)}k`;
  return `${sign}₹${abs.toFixed(0)}`;
}

export function pct(value: number | null, fractionDigits = 1): string {
  if (value === null || Number.isNaN(value)) return "n/a";
  return `${value.toFixed(fractionDigits)}%`;
}

export function ratio(value: number | null, fractionDigits = 2): string {
  if (value === null || Number.isNaN(value)) return "n/a";
  return `${value.toFixed(fractionDigits)}×`;
}

export function decimal(value: number | null, fractionDigits = 3): string {
  if (value === null || Number.isNaN(value)) return "—";
  return value.toFixed(fractionDigits);
}

export const BAND_COLOR: Record<string, string> = {
  CRITICAL: "text-rose-400 border-rose-500/40 bg-rose-500/10",
  HIGH: "text-orange-400 border-orange-500/40 bg-orange-500/10",
  MEDIUM: "text-yellow-300 border-yellow-500/40 bg-yellow-500/10",
  LOW: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
};

export const CONFIDENCE_COLOR: Record<string, string> = {
  HIGH: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
  MEDIUM: "text-yellow-300 border-yellow-500/40 bg-yellow-500/10",
  LOW: "text-rose-400 border-rose-500/40 bg-rose-500/10",
};
