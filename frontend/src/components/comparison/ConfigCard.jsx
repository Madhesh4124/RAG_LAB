import { useState } from "react";
import { Badge } from "../common/index";

export default function ConfigCard({ result }) {
  const [showChunks, setShowChunks] = useState(false);
  const { configName, params, answer, metrics, chunks, error } = result;
  
  // Handle error case
  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 overflow-hidden flex flex-col">
        <div className="bg-red-100 px-4 py-3 border-b border-red-200">
          <p className="font-semibold text-red-800 text-sm">{configName}</p>
        </div>
        <div className="px-4 py-3 flex-1">
          <p className="text-xs text-red-600 uppercase tracking-wide font-medium mb-1">Error</p>
          <p className="text-sm text-red-700">{error}</p>
        </div>
      </div>
    );
  }
  
  // Extract params from nested structure
  const chunking = params?.chunking || {};
  const embedding = params?.embedding || {};
  const retrieval = params?.retrieval || {};
  
  const strategy = chunking.type || params?.strategy || "unknown";
  const model = embedding.model || embedding.provider || params?.model || "unknown";
  const top_k = retrieval.top_k || params?.top_k || "N/A";
  const chunk_size = chunking.chunk_size || params?.chunk_size;

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden flex flex-col">

      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
        <p className="font-semibold text-gray-800 text-sm">{configName}</p>
        <div className="flex flex-wrap gap-1 mt-1.5">
          <Badge color="blue">{strategy}</Badge>
          <Badge color="gray">{model}</Badge>
          <Badge color="orange">top-{top_k}</Badge>
          {chunk_size && <Badge color="gray">{chunk_size}ch</Badge>}
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
          { label: "Time",       value: `${metrics.response_time_ms}ms` },
          { label: "Chunks",     value: metrics.chunks_retrieved },
          { label: "Similarity", value: metrics.avg_similarity?.toFixed(2) || "0.00" },
          { label: "Tokens",     value: metrics.token_count },
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
              <div key={c.id || i} className="rounded bg-blue-50 border border-blue-200 px-2 py-1.5">
                <p className="text-[10px] font-mono text-blue-500">#{i + 1} · {String(c.id).slice(0, 6)}</p>
                <p className="text-xs text-gray-600 mt-0.5 line-clamp-2">{c.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
