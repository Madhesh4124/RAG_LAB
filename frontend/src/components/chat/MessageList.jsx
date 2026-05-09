import { useState } from "react";

export default function MessageList({ messages }) {
  const [expandedChunks, setExpandedChunks] = useState({});

  const toggleChunks = (idx) => {
    setExpandedChunks((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  if (!messages.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-300">
        <div className="text-center">
          <div className="text-4xl mb-2">💬</div>
          <p className="text-sm">Ask a question about your document</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((msg, i) => (
        <div key={msg.id || i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
          <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm
            ${msg.role === "user"
              ? "bg-blue-600 text-white rounded-br-sm"
              : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"}`}>

            {/* Status line shown while waiting */}
            {msg.status && (
              <div className="flex items-center gap-2 text-xs text-blue-500 mb-2">
                <span className="inline-block w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                {msg.status}
              </div>
            )}

            {/* Answer text */}
            {msg.content
              ? <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              : !msg.status && <p className="leading-relaxed text-gray-300 italic">Thinking…</p>
            }

            {/* Retrieved chunks */}
            {msg.chunks?.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                <button
                  type="button"
                  onClick={() => toggleChunks(i)}
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                >
                  {expandedChunks[i] ? "Hide" : "Show"} Retrieved {msg.chunks.length} chunk{msg.chunks.length !== 1 ? "s" : ""}
                </button>

                {expandedChunks[i] && msg.chunks.map((chunk, j) => {
                  const score = typeof chunk.score === "number"
                    ? chunk.score
                    : typeof chunk.raw_score === "number"
                      ? chunk.raw_score
                      : null;
                  const rawScore = typeof chunk.raw_score === "number" ? chunk.raw_score : null;
                  const scoreColor =
                    score === null ? "text-gray-400"
                    : score >= 0.75 ? "text-emerald-600 font-semibold"
                    : score >= 0.5  ? "text-yellow-600"
                    : score > 0 ? "text-red-500"
                    : "text-gray-400";
                  const scoreLabel =
                    score === null ? "score unavailable"
                    : `${(score * 100).toFixed(1)} retrieval score`;
                  const rawScoreLabel =
                    rawScore === null || rawScore === score ? null
                    : `raw ${(rawScore * 100).toFixed(1)}`;
                  return (
                    <div key={j} className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 hover:border-blue-200 transition-colors">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-mono text-gray-400">#{j + 1}</span>
                        <span className={`text-xs ${scoreColor}`}>
                          {scoreLabel}
                          {rawScoreLabel ? ` · ${rawScoreLabel}` : ""}
                        </span>
                      </div>
                      {chunk.section_heading && (
                        <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                          {chunk.section_heading}
                        </p>
                      )}
                      <p className="text-xs text-gray-600 line-clamp-3 leading-relaxed">{chunk.text}</p>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Timings */}
            {msg.timings && Object.keys(msg.timings).length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-2">
                  Pipeline Timings
                </p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  {Object.entries(msg.timings).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="text-gray-400">{key.replace("_ms", "").replace(/_/g, " ")}</span>
                      <span className="font-mono text-gray-600">{Math.round(Number(val))}ms</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
