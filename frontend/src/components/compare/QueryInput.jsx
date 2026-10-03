import React from 'react';
import { Button } from "../common/index";
import { IconArrowRight } from "../common/Icons";

export default function QueryInput({ query, onChange, onRun, isLoading, isDisabled, stagedCount, isActivated }) {
  const canRun = query.trim().length > 0 && stagedCount >= 1 && !isLoading && !isDisabled;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-zinc-100">Benchmark Query Input</h2>
        <p className="text-xs text-zinc-400 mt-0.5">
          Send a query concurrently to all staged pipelines to measure response diff, token latency, and retrieval relevance.
        </p>
      </div>

      <div className={`rounded-lg border border-zinc-800 bg-zinc-950 p-3 transition-colors focus-within:border-zinc-700 ${isDisabled ? "opacity-50" : ""}`}>
        <textarea
          value={query}
          onChange={(e) => onChange(e.target.value)}
          disabled={isDisabled || isLoading}
          rows={3}
          placeholder={
            isActivated
              ? "Enter your evaluation query to compare across staged pipelines…"
              : "Stage configurations and click 'Run & Save Staged Configs' first to unlock."
          }
          className="w-full bg-transparent text-xs text-zinc-100 placeholder-zinc-500 outline-none resize-none leading-relaxed"
        />
      </div>

      <div className="mt-3.5 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-zinc-500 font-mono">
          {isActivated
            ? `Ready to evaluate across ${stagedCount} active configuration${stagedCount !== 1 ? "s" : ""}.`
            : "Requires indexed staged configurations."}
        </p>

        <Button
          onClick={onRun}
          disabled={!canRun}
          size="sm"
          trailingIcon={!isLoading ? <IconArrowRight size={11} /> : null}
        >
          {isLoading ? (
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-zinc-900 border-t-zinc-950" />
              Evaluating…
            </span>
          ) : (
            "Run Benchmark"
          )}
        </Button>
      </div>
    </div>
  );
}
