import React from 'react';
import { Badge, Button } from "../common/index";

const statusConfig = {
  indexing:       { label: "Indexing…",       color: "amber",   dot: "bg-amber-400 animate-pulse" },
  ready:          { label: "Ready",           color: "emerald", dot: "bg-emerald-400" },
  already_exists: { label: "Indexed",         color: "emerald", dot: "bg-emerald-400" },
  error:          { label: "Failed",          color: "red",     dot: "bg-red-400" },
  idle:           { label: "Not indexed",     color: "ghost",   dot: "bg-zinc-600" },
};

export default function ConfigCard({ config, onAdd, isStaged, disabled }) {
  const chunkParamEntries = Object.entries(config.chunk_params || {}).slice(0, 3);
  const status = config.indexingStatus || "idle";
  const { label: statusLabel, color: statusColor, dot: dotClass } = statusConfig[status] || statusConfig.idle;
  const canAdd = !disabled && !isStaged && status !== "indexing";

  return (
    <div className="flex flex-col justify-between rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 hover:border-zinc-700 hover:bg-zinc-900 transition-colors">
      <div>
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 font-mono text-[10px] text-zinc-500 uppercase tracking-wider mb-1">
              <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
              <span>{config.isPreset ? "System Preset" : "Custom Config"}</span>
            </div>
            <h3 className="text-sm font-semibold text-zinc-100 truncate">{config.name}</h3>
          </div>

          <Button
            onClick={onAdd}
            disabled={!canAdd}
            size="sm"
            variant={isStaged ? "secondary" : "primary"}
          >
            {isStaged ? "Staged ✓" : "+ Stage"}
          </Button>
        </div>

        {/* Parameters tags */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          <Badge color="blue">{config.chunk_strategy}</Badge>
          <Badge color="ghost">k: {config.top_k}</Badge>
          <Badge color="ghost">thr: {Number(config.threshold).toFixed(2)}</Badge>
          {chunkParamEntries.map(([key, val]) => (
            <Badge key={key} color="ghost">
              {key}: {Array.isArray(val) ? `[${val.length}]` : String(val)}
            </Badge>
          ))}
        </div>

        {/* Model info */}
        <div className="font-mono text-[10px] text-zinc-500 bg-zinc-950/70 p-2 rounded border border-zinc-800/80 truncate">
          <span className="text-zinc-600 block text-[9px] uppercase">Embedding Model</span>
          <span className="text-zinc-300">{config.embedding_model}</span>
        </div>
      </div>

      {/* Footer status */}
      <div className="mt-4 pt-3 border-t border-zinc-800/70 flex items-center justify-between text-xs font-mono">
        <span className="text-zinc-500 text-[11px]">Collection Status:</span>
        <Badge color={statusColor}>{statusLabel}</Badge>
      </div>
    </div>
  );
}
