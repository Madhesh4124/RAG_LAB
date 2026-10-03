import React, { useState } from "react";
import { IconSparkle, IconImage, IconChevronRight, IconDocument } from "../common/Icons";
import { BASE_URL } from "../../services/api";

const scoreStyle = (score) => {
  if (score === null || score === undefined) return "text-zinc-500 border-zinc-800 bg-zinc-900";
  if (score >= 0.75) return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
  if (score >= 0.5)  return "text-amber-400 border-amber-500/30 bg-amber-500/10";
  return "text-red-400 border-red-500/30 bg-red-500/10";
};

export default function MessageList({ messages }) {
  const [expandedChunks, setExpandedChunks] = useState({});

  const toggleChunks = (idx) =>
    setExpandedChunks((prev) => ({ ...prev, [idx]: !prev[idx] }));

  if (!messages.length) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-500 mb-3">
          <IconDocument size={18} />
        </div>
        <p className="text-sm font-medium text-zinc-300">Ready for Document QA</p>
        <p className="mt-1 text-xs text-zinc-500 max-w-xs">
          Ask questions to query against your indexed vectors with cited source chunks.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5 py-4">
      {messages.map((msg, i) => (
        <div
          key={msg.id || i}
          className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          {/* Assistant icon */}
          {msg.role === "assistant" && (
            <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-zinc-900 border border-zinc-800 text-amber-500 mt-0.5">
              <IconSparkle size={13} />
            </div>
          )}

          <div
            className={`max-w-[85%] text-xs leading-relaxed ${
              msg.role === "user"
                ? "bg-amber-500/15 border border-amber-500/25 text-zinc-100 px-4 py-3 rounded-xl"
                : "bg-zinc-900/80 border border-zinc-800/90 text-zinc-200 px-4 py-3.5 rounded-xl shadow-sm"
            }`}
          >
            {/* Status notification */}
            {msg.status && (
              <div className="flex items-center gap-2 font-mono text-[11px] text-amber-400 mb-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />
                <span>{msg.status}</span>
              </div>
            )}

            {/* Content text */}
            {msg.content ? (
              <div className="whitespace-pre-wrap leading-relaxed text-zinc-100 font-sans text-xs">
                {msg.content}
              </div>
            ) : (
              !msg.status && <p className="text-zinc-500 italic text-xs">Generating response…</p>
            )}

            {/* Retrieved chunks citation block */}
            {msg.chunks?.length > 0 && (
              <div className="mt-3.5 pt-3 border-t border-zinc-800/80">
                <button
                  type="button"
                  onClick={() => toggleChunks(i)}
                  className="flex items-center gap-1.5 font-mono text-[10px] text-zinc-400 hover:text-zinc-200 transition-colors uppercase tracking-wider cursor-pointer"
                  aria-expanded={expandedChunks[i]}
                >
                  <IconChevronRight
                    size={11}
                    className={`transition-transform duration-200 ${expandedChunks[i] ? "rotate-90" : ""}`}
                  />
                  <span>
                    {expandedChunks[i] ? "Hide" : "Inspect"} {msg.chunks.length} Retrieved Chunk{msg.chunks.length !== 1 ? "s" : ""}
                  </span>
                </button>

                {expandedChunks[i] && (
                  <div className="mt-2.5 space-y-2">
                    {msg.chunks.map((chunk, j) => {
                      const score = typeof chunk.score === "number" ? chunk.score : chunk.raw_score;
                      return (
                        <div
                          key={j}
                          className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-3 text-xs"
                        >
                          <div className="flex items-center justify-between gap-2 mb-1.5 pb-1 border-b border-zinc-800/60 font-mono text-[10px]">
                            <span className="text-zinc-500 font-medium">CHUNK #{j + 1}</span>
                            <span className={`px-1.5 py-0.5 rounded border text-[10px] font-semibold ${scoreStyle(score)}`}>
                              {score !== null && score !== undefined ? `${(score * 100).toFixed(1)}% match` : "Score N/A"}
                            </span>
                          </div>

                          {chunk.section_heading && (
                            <p className="font-semibold text-zinc-300 text-[11px] mb-1">
                              {chunk.section_heading}
                            </p>
                          )}

                          {chunk.image_url ? (
                            <div className="mt-2 space-y-1.5">
                              <div className="flex items-center gap-1 font-mono text-[10px] text-amber-400">
                                <IconImage size={11} />
                                <span>Visual Figure {chunk.metadata?.page ? `(Page ${chunk.metadata.page})` : ""}</span>
                              </div>
                              <div className="rounded border border-zinc-800 bg-zinc-900 p-1">
                                <img
                                  src={chunk.image_url.startsWith("http") ? chunk.image_url : `${BASE_URL}${chunk.image_url}`}
                                  alt={chunk.section_heading || "Extracted figure"}
                                  className="max-h-56 w-auto object-contain rounded"
                                  onError={(e) => { e.currentTarget.style.display = "none"; }}
                                />
                              </div>
                            </div>
                          ) : (
                            <div className="font-mono text-[11px] text-zinc-300 leading-relaxed bg-zinc-900/50 p-2.5 rounded border border-zinc-800/40 overflow-x-auto max-h-64 whitespace-pre-wrap">
                              {chunk.text}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Pipeline timings */}
            {msg.timings && Object.keys(msg.timings).length > 0 && (
              <div className="mt-3 pt-2.5 border-t border-zinc-800/60 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[10px] text-zinc-500">
                {Object.entries(msg.timings).map(([key, val]) => (
                  <span key={key}>
                    {key.replace("_ms", "")}: <span className="text-zinc-300">{Math.round(Number(val))}ms</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
