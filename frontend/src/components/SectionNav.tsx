"use client";

import { useEffect, useState } from "react";

export const SECTIONS = [
  { id: "briefing", label: "Briefing", key: "1" },
  { id: "scenarios", label: "Scenarios", key: "2" },
  { id: "optimizer", label: "Optimizer", key: "3" },
  { id: "compliance", label: "Compliance", key: "4" },
  { id: "ask", label: "Ask", key: "5" },
  { id: "confidence", label: "Data", key: "6" },
] as const;

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  return (
    el.tagName === "INPUT" ||
    el.tagName === "TEXTAREA" ||
    el.tagName === "SELECT" ||
    el.isContentEditable
  );
}

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

/**
 * Section nav with scroll-spy and keyboard jumps.
 *
 * Two reasons this is not decoration. The dashboard is a long single page, so without
 * landmarks a reader loses their place; and a live demo is driven from the keyboard, so
 * pressing a number to jump beats hunting for a scrollbar under time pressure.
 */
export function SectionNav() {
  const [active, setActive] = useState<string>(SECTIONS[0].id);

  // Scroll-spy: mark whichever section occupies the upper reading band.
  useEffect(() => {
    const visible = new Map<string, number>();

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) visible.set(entry.target.id, entry.boundingClientRect.top);
          else visible.delete(entry.target.id);
        }
        if (visible.size === 0) return;
        const [topmost] = [...visible.entries()].sort((a, b) => a[1] - b[1]);
        setActive(topmost[0]);
      },
      // A band across the upper third: a section is "current" once it reaches reading height,
      // and stops being current when the next one does.
      { rootMargin: "-15% 0px -70% 0px", threshold: 0 },
    );

    for (const section of SECTIONS) {
      const element = document.getElementById(section.id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (isTyping(event.target)) {
        // Let Escape leave a text field, so `/` can be used again without reaching for the mouse.
        if (event.key === "Escape") (event.target as HTMLElement).blur();
        return;
      }

      const section = SECTIONS.find((candidate) => candidate.key === event.key);
      if (section) {
        event.preventDefault();
        scrollTo(section.id);
        return;
      }
      if (event.key === "/") {
        event.preventDefault();
        const input = document.getElementById("ask-input");
        input?.scrollIntoView({ behavior: "smooth", block: "center" });
        (input as HTMLInputElement | null)?.focus();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <nav
      aria-label="Dashboard sections"
      className="sticky top-0 z-20 -mx-4 flex flex-wrap items-center gap-1 border-b border-white/[0.06] bg-[#05070d]/85 px-4 py-2 backdrop-blur-md sm:-mx-6 sm:px-6"
    >
      {SECTIONS.map((section) => {
        const isActive = section.id === active;
        return (
          <a
            key={section.id}
            href={`#${section.id}`}
            aria-current={isActive ? "true" : undefined}
            className={`rounded-full border px-3 py-1 text-[11px] transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400 ${
              isActive
                ? "border-cyan-400/50 bg-cyan-500/10 text-cyan-200"
                : "border-white/10 text-slate-400 hover:border-white/25 hover:text-slate-200"
            }`}
          >
            {section.label}
          </a>
        );
      })}
      <span className="ml-auto hidden font-mono text-[10px] text-slate-600 lg:inline">
        press 1–6 to jump · / to ask
      </span>
    </nav>
  );
}
