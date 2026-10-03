import React from 'react';
import { IconCheck, IconDocument } from "../common/Icons";

export default function DatasetBanner({ activeDataset, isDisabled }) {
  if (activeDataset) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <IconCheck size={14} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-zinc-500 uppercase tracking-wider">Active Evaluation Dataset</span>
            </div>
            <p className="text-sm font-semibold text-zinc-100 mt-0.5">{activeDataset}</p>
          </div>
        </div>
        <div className="font-mono text-xs text-emerald-400/90 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>Ready for Comparison</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border p-4 flex items-center gap-3 ${
      isDisabled
        ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
        : "border-zinc-800 bg-zinc-900/50 text-zinc-400"
    }`}>
      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
        <IconDocument size={16} />
      </div>
      <div>
        <p className="text-xs font-medium text-amber-300">
          No dataset loaded for comparison
        </p>
        <p className="text-[11px] text-amber-400/70 mt-0.5">
          Please upload or load a document below to benchmark retrieval and answer quality across configs.
        </p>
      </div>
    </div>
  );
}
