import React from 'react';
import { useEffect, useState } from "react";
import { Button } from "../common/index";

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
  const hasIndexing = stagedConfigs.some((config) => config.indexingStatus === "indexing");

  useEffect(() => {
    if (!stagedConfigs.length) {
      setLoadingProgressByName({});
      return;
    }

    setLoadingProgressByName((prev) => {
      const next = { ...prev };
      for (const config of stagedConfigs) {
        if (config.indexingStatus === "indexing" && next[config.name] == null) {
          next[config.name] = 6;
        }
        if (config.indexingStatus !== "indexing" && next[config.name] == null) {
          next[config.name] = 0;
        }
      }
      return next;
    });

    if (!hasIndexing) return;

    const interval = window.setInterval(() => {
      setLoadingProgressByName((prev) => {
        const next = { ...prev };
        for (const config of stagedConfigs) {
          if (config.indexingStatus !== "indexing") {
            continue;
          }

          const current = Number(next[config.name] ?? 6);
          // Fast initial fill, then slow near completion.
          const delta = current < 60 ? 3 : current < 85 ? 1.5 : 0.4;
          next[config.name] = Math.min(94, current + delta);
        }
        return next;
      });
    }, 140);

    return () => window.clearInterval(interval);
  }, [hasIndexing, stagedConfigs]);

  const statusLabel = (status) => {
    if (status === "indexing") return "Indexing...";
    if (status === "ready") return "Ready";
    if (status === "already_exists") return "Already indexed";
    if (status === "error") return "Index failed";
    return "Not indexed";
  };

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Staging Panel</h2>
          <p className="text-sm text-gray-500">Prepare up to four configs for a side-by-side comparison.</p>
        </div>
        <div className="text-sm text-gray-500">{stagedConfigs.length} / 4 configs staged</div>
      </div>

      <div className="mt-4 space-y-2">
        {stagedConfigs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-sm text-gray-400">
            No configs staged yet.
          </div>
        ) : (
          stagedConfigs.map((config) => (
            <div key={config.name} className="rounded-xl border border-gray-200 px-4 py-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{config.name}</p>
                  <p className="text-sm text-gray-500">top_k: {config.top_k} · threshold: {Number(config.threshold).toFixed(2)}</p>
                  <p className="mt-1 text-xs text-gray-400">{statusLabel(config.indexingStatus)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(config.name)}
                  disabled={isDisabled}
                  className="rounded-full px-2 py-1 text-sm text-gray-500 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
                  aria-label={`Remove ${config.name}`}
                >
                  ❌
                </button>
              </div>

              {config.indexingStatus === "indexing" && (
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-blue-100">
                  <div
                    className="h-full rounded-full bg-blue-500 transition-[width] duration-150"
                    style={{ width: `${Math.max(6, Number(loadingProgressByName[config.name] ?? 6))}%` }}
                  />
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <Button onClick={onRunStaged} disabled={!isRunEnabled}>
          {isRunningStaged ? "Running & Saving..." : "Run & Save Configs"}
        </Button>
        <Button variant="secondary" onClick={onClearAll} disabled={isDisabled || stagedConfigs.length === 0}>
          Clear All
        </Button>
      </div>
    </section>
  );
}
