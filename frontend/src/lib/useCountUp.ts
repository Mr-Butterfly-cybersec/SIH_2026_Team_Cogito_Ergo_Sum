"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Animate a number from 0 to its target over `duration` ms.
 *
 * Used for the headline figures only. A count-up makes a dashboard feel like it is
 * *measuring* something rather than displaying a static label — but it also delays the
 * reader, so it is deliberately short and it lands exactly on the true value (no
 * interpolation residue).
 *
 * Respects `prefers-reduced-motion`: motion-sensitive users get the final value immediately.
 * Values are never rounded *to* something else — the end state is the real figure.
 */
export function useCountUp(target: number, duration = 700): number {
  const [value, setValue] = useState(0);
  const frame = useRef<number | null>(null);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduced || !Number.isFinite(target) || target === 0) {
      // Jump straight to the value, but still via rAF: calling setState synchronously in an
      // effect body triggers a cascading render, which React and the lint rule both flag.
      const immediate = requestAnimationFrame(() => setValue(target));
      return () => cancelAnimationFrame(immediate);
    }

    const start = performance.now();
    const from = 0;

    function tick(now: number) {
      const progress = Math.min((now - start) / duration, 1);
      // Ease-out cubic: fast start, gentle settle — reads as "arriving" rather than "sliding".
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(from + (target - from) * eased);
      if (progress < 1) frame.current = requestAnimationFrame(tick);
      else setValue(target);
    }

    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    };
  }, [target, duration]);

  return value;
}
