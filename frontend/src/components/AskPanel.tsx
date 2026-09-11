"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Card, ErrorState } from "@/components/ui";
import { api } from "@/lib/api";

const SUGGESTIONS = [
  "What is our highest financial cyber risk?",
  "What can we do with ₹25 lakh?",
  "What happens if we delay patching for 30 days?",
  "Why is MFA recommended before SIEM expansion?",
  "Are we compliant with RBI?",
];

export function AskPanel() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<
    { question: string; answer: string; provider: string; degraded: boolean; tools: string[] }[]
  >([]);

  const status = useQuery({ queryKey: ["ai-status"], queryFn: api.aiStatus });

  const ask = useMutation({
    mutationFn: (q: string) => api.ask(q),
    onSuccess: (data, q) => {
      setHistory((prev) => [
        ...prev,
        {
          question: q,
          answer: data.answer,
          provider: data.provider,
          degraded: data.degraded,
          tools: data.tool_calls.map((t) => t.name),
        },
      ]);
      setQuestion("");
    },
  });

  const submit = (q: string) => {
    if (!q.trim() || ask.isPending) return;
    ask.mutate(q.trim());
  };

  return (
    <Card
      title="Ask the engine"
      action={
        status.data ? (
          <Badge
            className={
              status.data.active.length > 0
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : "border-amber-500/40 bg-amber-500/10 text-amber-300"
            }
          >
            {status.data.active.length > 0
              ? `${status.data.active[0]} active`
              : "deterministic mode"}
          </Badge>
        ) : null
      }
    >
      <p className="mb-3 text-[11px] leading-snug text-slate-500">
        The language model never computes a number — it selects a tool, the deterministic engine
        runs, and the result is turned into prose. Every answer ships with the tool calls that
        produced it.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(question);
        }}
        className="flex gap-2"
      >
        <input
          id="ask-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What can we do with ₹25 lakh?"
          aria-label="Ask the risk engine a question"
          maxLength={500}
          className="flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-600 focus:border-cyan-400/60"
        />
        <button
          type="submit"
          disabled={ask.isPending || !question.trim()}
          className="rounded-lg border border-cyan-400/40 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/20 disabled:opacity-40"
        >
          {ask.isPending ? "Asking…" : "Ask"}
        </button>
      </form>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => submit(s)}
            className="rounded-full border border-white/10 px-2.5 py-1 text-[10px] text-slate-400 transition hover:border-white/25 hover:text-slate-200"
          >
            {s}
          </button>
        ))}
      </div>

      {ask.isError ? (
        <ErrorState message={`The question could not be answered — ${(ask.error as Error).message}`} compact />
      ) : null}

      <div className="mt-4 space-y-3" aria-live="polite">
        {history
          .slice()
          .reverse()
          .map((entry, index) => (
            <div key={`${entry.question}-${index}`} className="rounded-xl border border-white/5 bg-black/20 p-3">
              <p className="text-[11px] font-medium text-slate-300">{entry.question}</p>
              <p className="mt-1.5 whitespace-pre-line text-[13px] leading-relaxed text-slate-100">
                {entry.answer}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <Badge className="border-white/15 bg-white/5 text-slate-400">
                  {entry.provider}
                </Badge>
                {entry.degraded ? (
                  <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-300">
                    no LLM
                  </Badge>
                ) : null}
                {entry.tools.map((tool) => (
                  <span
                    key={tool}
                    className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-slate-500"
                  >
                    {tool}()
                  </span>
                ))}
              </div>
            </div>
          ))}
      </div>
    </Card>
  );
}
