import { useState } from "react";
import { Badge } from "../common/index";

function scoreColor(score) {
  if (score > 0.7) return "green";
  if (score >= 0.4) return "yellow";
  return "red";
}

function formatScore(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0.0000";
  return num.toFixed(4);
}

export default function ResultCard({ result }) {
  const [expandedChunks, setExpandedChunks] = useState({});

  const toggleChunk = (index) => {
    setExpandedChunks((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  return (
    <article className="flex h-full min-w-[320px] flex-col rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
        <h3 className="text-base font-semibold text-gray-900">{result.config?.name}</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge color="blue">top_k: {result.config?.top_k}</Badge>
          <Badge color="gray">threshold: {Number(result.config?.threshold ?? 0).toFixed(2)}</Badge>
          <Badge color="orange">{result.config?.chunk_strategy}</Badge>
          <Badge color="gray">{result.config?.embedding_model}</Badge>
          <Badge color="gray">{result.config?.collection_name}</Badge>
        </div>
      </div>

      <div className="space-y-4 p-4">
        <section>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Answer</p>
          <div className="mt-2 rounded-xl border border-gray-100 bg-gray-50 p-3 text-sm leading-relaxed text-gray-800 whitespace-pre-wrap">
            {result.answer}
          </div>
        </section>

        <section className="grid grid-cols-3 gap-2 rounded-xl border border-gray-100 bg-gray-50 p-3 text-sm">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-gray-400">⏱ Latency</p>
            <p className="font-mono text-gray-800">{Math.round(Number(result.latency_ms ?? 0))}ms</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-gray-400">📊 Avg Score</p>
            <p className="font-mono text-gray-800">{formatScore(result.avg_similarity)}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-gray-400">📦 Chunks</p>
            <p className="font-mono text-gray-800">{result.chunk_count}</p>
          </div>
        </section>

        <section>
          <button
            type="button"
            onClick={() => toggleChunk("all")}
            className="text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            {expandedChunks.all ? "Hide" : "Show"} Retrieved Chunks
          </button>

          {expandedChunks.all && (
            <div className="mt-3 space-y-3">
              {result.chunks.map((chunk, index) => {
                const score = Number(result.scores?.[index] ?? 0);
                const color = scoreColor(score);
                return (
                  <div key={`${result.config?.name}-${index}`} className="rounded-xl border border-gray-200 bg-white p-3">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <Badge color={color}>{formatScore(score)} match</Badge>
                      <button
                        type="button"
                        onClick={() => toggleChunk(index)}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        {expandedChunks[index] ? "Collapse" : "Expand"}
                      </button>
                    </div>
                    <p className={`text-sm text-gray-700 leading-relaxed ${expandedChunks[index] ? "whitespace-pre-wrap" : "line-clamp-3"}`}>
                      {chunk}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </article>
  );
}
