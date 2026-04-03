import { useState } from "react";
import { Badge } from "../common/index";

export default function ConfigCard({ result }) {
  const [showChunks, setShowChunks] = useState(false);
  const { config, answer, chunks, scores, error, latency_ms, avg_similarity, chunk_count } = result;
  const responseTimeMs = Number.isFinite(Number(latency_ms))
    ? Math.round(Number(latency_ms))
    : 0;
  
  // Handle error case
  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 overflow-hidden flex flex-col">
        <div className="bg-red-100 px-4 py-3 border-b border-red-200">
          <p className="font-semibold text-red-800 text-sm">{config?.name || "Configuration"}</p>
        </div>
        <div className="px-4 py-3 flex-1">
          <p className="text-xs text-red-600 uppercase tracking-wide font-medium mb-1">Error</p>
          <p className="text-sm text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden flex flex-col">

      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
        <p className="font-semibold text-gray-800 text-sm">{config?.name || "Configuration"}</p>
        <div className="flex flex-wrap gap-1 mt-1.5">
          <Badge color="orange">top-{config?.top_k}</Badge>
          <Badge color="blue">threshold {Number(config?.threshold ?? 0).toFixed(2)}</Badge>
        </div>
      </div>

      {/* Answer */}
      <div className="px-4 py-3 flex-1">
        <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">Answer</p>
        <p className="text-sm text-gray-700 leading-relaxed">{answer}</p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-px bg-gray-100 border-t border-gray-200">
        {[
          { label: "Time",       value: `${responseTimeMs}ms` },
          { label: "Chunks",     value: chunk_count ?? 0 },
          { label: "Similarity", value: Number(avg_similarity ?? 0).toFixed(4) },
          { label: "Scores",     value: scores?.length ?? 0 },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white px-3 py-2">
            <p className="text-[10px] text-gray-400 uppercase">{label}</p>
            <p className="text-sm font-mono font-semibold text-gray-800">{value}</p>
          </div>
        ))}
      </div>

      {/* Retrieved chunks toggle */}
      <div className="border-t border-gray-100">
        <button
          onClick={() => setShowChunks((s) => !s)}
          className="w-full text-xs text-gray-400 hover:text-gray-600 py-2 transition-colors"
        >
          {showChunks ? "▲ Hide" : "▼ Show"} retrieved chunks ({chunks?.length || 0})
        </button>
        {showChunks && chunks && chunks.length > 0 && (
          <div className="px-3 pb-3 space-y-2">
            {chunks.map((c, i) => (
              <div key={i} className="rounded bg-blue-50 border border-blue-200 px-2 py-1.5">
                <p className="text-[10px] font-mono text-blue-500">#{i + 1} · score {Number(scores?.[i] ?? 0).toFixed(4)}</p>
                <p className="text-xs text-gray-600 mt-0.5 line-clamp-3">{c}</p>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
