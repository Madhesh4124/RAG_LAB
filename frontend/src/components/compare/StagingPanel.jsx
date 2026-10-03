import React, { useEffect, useState } from "react";
import { Button } from "../common/index";
import { IconArrowRight, IconClose } from "../common/Icons";

export default function StagingPanel({
  stagedConfigs,
  onRemove,
  onClearAll,
  onRunStaged,
  isDisabled,
  isRunningStaged,
  isRunEnabled,
}) {
  const [loadingProgressByName, setLoadingProgressByName] = useState({});
  const hasIndexing = stagedConfigs.some((c) => c.indexingStatus === "indexing");

  useEffect(() => {
    if (!stagedConfigs.length) { setLoadingProgressByName({}); return; }
    setLoadingProgressByName((prev) => {
      const next = { ...prev };
      for (const config of stagedConfigs) {
        if (config.indexingStatus === "indexing" && next[config.name] == null) next[config.name] = 6;
        if (config.indexingStatus !== "indexing" && next[config.name] == null) next[config.name] = 0;
      }
      return next;
    });
    if (!hasIndexing) return;
    const interval = window.setInterval(() => {
      setLoadingProgressByName((prev) => {
        const next = { ...prev };
        for (const config of stagedConfigs) {
          if (config.indexingStatus !== "indexing") continue;
          const current = Number(next[config.name] ?? 6);
          const delta = current < 60 ? 3 : current < 85 ? 1.5 : 0.4;
          next[config.name] = Math.min(94, current + delta);
        }
        return next;
      });
    }, 140);
    return () => window.clearInterval(interval);
  }, [hasIndexing, stagedConfigs]);

  const statusLabel = (status) => {
    if (status === "indexing")       return { text: "Indexing…",       color: "text-amber-400" };
    if (status === "ready")          return { text: "Ready",           color: "text-emerald-400" };
    if (status === "already_exists") return { text: "Already indexed", color: "text-emerald-400" };
    if (status === "error")          return { text: "Index failed",    color: "text-red-400" };
    return { text: "Pending indexing", color: "text-zinc-500" };
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-zinc-100">Comparison Staging Queue</h2>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/60">
              {stagedConfigs.length} / 4
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-0.5">
            Stage up to 4 configurations to run concurrently against your evaluation dataset.
          </p>
        </div>
      </div>

      {/* Items list */}
      <div className="space-y-2">
        {stagedConfigs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-zinc-800 p-6 text-center text-xs text-zinc-500">
            No configurations staged yet. Click <span className="text-zinc-300 font-medium">+ Stage</span> on any card above.
          </div>
        ) : (
          stagedConfigs.map((config) => {
            const { text, color } = statusLabel(config.indexingStatus);
            const pct = Math.max(6, Number(loadingProgressByName[config.name] ?? 6));
            return (
              <div
                key={config.name}
                className="rounded-lg border border-zinc-800 bg-zinc-950/80 px-4 py-3 hover:border-zinc-700/80 transition-colors"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-zinc-200 text-xs truncate">{config.name}</p>
                      <span className={`font-mono text-[10px] ${color}`}>● {text}</span>
                    </div>
                    <p className="font-mono text-[10px] text-zinc-500 mt-0.5 truncate">
                      top_k: {config.top_k} · threshold: {Number(config.threshold).toFixed(2)} · {config.embedding_model}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onRemove(config.name)}
                    disabled={isDisabled}
                    className="h-6 w-6 rounded flex items-center justify-center text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                    aria-label={`Remove ${config.name}`}
                  >
                    <IconClose size={12} />
                  </button>
                </div>
                {config.indexingStatus === "indexing" && (
                  <div className="mt-2 h-1 w-full rounded-full bg-zinc-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-amber-500 transition-all duration-150"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Actions */}
      <div className="mt-4 pt-3 border-t border-zinc-800/80 flex items-center justify-end gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={onClearAll}
          disabled={isDisabled || stagedConfigs.length === 0}
        >
          Clear Staging
        </Button>
        <Button
          size="sm"
          onClick={onRunStaged}
          disabled={!isRunEnabled}
          trailingIcon={!isRunningStaged ? <IconArrowRight size={11} /> : null}
        >
          {isRunningStaged ? "Indexing & Saving…" : "Run & Save Staged Configs"}
        </Button>
      </div>
    </div>
  );
}
