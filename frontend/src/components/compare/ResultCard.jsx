import React, { useState } from 'react';
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

export default function ResultCard({ result, onOpenEvaluation }) {
  const [expandedChunks, setExpandedChunks] = useState({});
  const [copiedIndex, setCopiedIndex] = useState(null);

  // Normalize chunks list from chunk_details or chunks array
  const rawChunks = Array.isArray(result.chunk_details) && result.chunk_details.length > 0
    ? result.chunk_details
    : Array.isArray(result.chunks)
      ? result.chunks.map((item, idx) => {
          if (typeof item === 'object' && item !== null) {
            return {
              index: idx + 1,
              text: item.text || item.content || JSON.stringify(item),
              score: result.scores?.[idx] ?? item.score ?? 0,
              page_number: item.page_number || item.page || item.metadata?.page_number,
              filename: item.filename || item.metadata?.filename,
              chunk_strategy: item.chunk_strategy || result.config?.chunk_strategy,
            };
          }
          return {
            index: idx + 1,
            text: String(item ?? ''),
            score: result.scores?.[idx] ?? 0,
            page_number: null,
            filename: null,
            chunk_strategy: result.config?.chunk_strategy,
          };
        })
      : [];

  const toggleChunk = (index) => {
    setExpandedChunks((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  const toggleAllChunks = () => {
    const nextState = !expandedChunks.all;
    const updated = { all: nextState };
    rawChunks.forEach((_, idx) => {
      updated[idx] = nextState;
    });
    setExpandedChunks(updated);
  };

  const copyChunkText = (text, idx) => {
    navigator.clipboard?.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 1800);
  };

  const hasStalePdfPointer = rawChunks.some((c) => String(c.text || '').startsWith('pdf://'));

  return (
    <article className="flex h-full min-w-[320px] flex-col rounded-2xl border border-white/10 bg-zinc-900/70 backdrop-blur-md shadow-xl transition-all hover:border-white/20">
      {/* Card Header */}
      <div className="border-b border-white/[0.08] bg-zinc-950/60 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-base font-semibold text-zinc-100">{result.config?.name}</h3>
          {result.evaluation?.answer_metrics?.faithfulness != null && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-300 border border-emerald-500/30">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              {(result.evaluation.answer_metrics.faithfulness * 100).toFixed(0)}% Grounded
            </span>
          )}
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Badge color="blue">top_k: {result.config?.top_k}</Badge>
          <Badge color="gray">threshold: {Number(result.config?.threshold ?? 0).toFixed(2)}</Badge>
          <Badge color="orange">{result.config?.chunk_strategy}</Badge>
          <Badge color="gray">{result.config?.embedding_model}</Badge>
        </div>
      </div>

      <div className="flex-1 space-y-4 p-4">
        {/* Answer Section */}
        <section>
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-400">Answer</p>
          <div className="mt-2 rounded-xl border border-white/[0.08] bg-zinc-950/60 p-3.5 text-sm leading-relaxed text-zinc-200 whitespace-pre-wrap selection:bg-accent-violet/30">
            {result.answer || <span className="italic text-zinc-500">No answer generated.</span>}
          </div>
        </section>

        {/* Quick Stats Grid */}
        <section className="grid grid-cols-3 gap-2 rounded-xl border border-white/[0.06] bg-zinc-950/40 p-3 text-sm">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">⏱ Latency</p>
            <p className="font-mono text-zinc-200 mt-0.5">{Math.round(Number(result.latency_ms ?? 0))}ms</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">📊 Avg Score</p>
            <p className="font-mono text-zinc-200 mt-0.5">{formatScore(result.avg_similarity)}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">📦 Chunks</p>
            <p className="font-mono text-zinc-200 mt-0.5">{rawChunks.length}</p>
          </div>
        </section>

        {/* Evaluation CTA */}
        <section className="flex items-center justify-between pt-1">
          <span className="text-xs text-zinc-500">
            {result.evaluation ? "Evaluation ready" : "Evaluation pending"}
          </span>
          <button
            type="button"
            onClick={() => onOpenEvaluation?.(result)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-accent-violet/30 bg-accent-violet/15 px-3 py-1.5 text-xs font-medium text-accent-violet-light transition-colors hover:bg-accent-violet/25 cursor-pointer"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20v-6M6 20V10M18 20V4" />
            </svg>
            Inspect Report
          </button>
        </section>

        {/* Retrieved Chunks Section */}
        <section className="border-t border-white/[0.08] pt-3">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={toggleAllChunks}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent-violet-light hover:text-accent-violet transition-colors cursor-pointer"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`transition-transform duration-200 ${expandedChunks.all ? "rotate-90" : ""}`}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              {expandedChunks.all ? "Hide" : "Show"} Retrieved Chunks ({rawChunks.length})
            </button>

            {expandedChunks.all && rawChunks.length > 0 && (
              <span className="text-[11px] text-zinc-500 font-mono">
                Sorted by similarity
              </span>
            )}
          </div>

          {hasStalePdfPointer && (
            <div className="mt-2.5 rounded-lg border border-amber-500/30 bg-amber-950/30 p-2.5 text-xs text-amber-300 leading-snug">
              ⚠️ <strong>Stale Index Detected:</strong> Chunks contain raw storage keys (<code>pdf://...</code>). Click <strong>"Clear Entire ChromaDB"</strong> above and re-run staged configs to re-index the extracted text.
            </div>
          )}

          {expandedChunks.all && (
            <div className="mt-3 space-y-3">
              {rawChunks.length === 0 ? (
                <div className="rounded-xl border border-dashed border-white/10 bg-zinc-950/40 p-4 text-center text-xs text-zinc-500">
                  No chunks were retrieved above the similarity threshold ({Number(result.config?.threshold ?? 0).toFixed(2)}).
                </div>
              ) : (
                rawChunks.map((chunk, index) => {
                  const score = Number(chunk.score ?? result.scores?.[index] ?? 0);
                  const color = scoreColor(score);
                  const isExpanded = expandedChunks[index] ?? true;
                  const text = chunk.text || "";
                  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

                  return (
                    <div
                      key={`${result.config?.name}-chunk-${index}`}
                      className="rounded-xl border border-white/[0.08] bg-zinc-950/60 p-3 shadow-xs hover:border-white/20 transition-all"
                    >
                      {/* Chunk Header */}
                      <div className="mb-2 flex flex-wrap items-center justify-between gap-1.5">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="rounded bg-white/[0.06] border border-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] font-medium text-zinc-400">
                            #{index + 1}
                          </span>
                          <Badge color={color}>{formatScore(score)} match</Badge>
                          {chunk.page_number && (
                            <span className="rounded bg-purple-500/15 border border-purple-500/30 px-1.5 py-0.5 text-[10px] font-medium text-purple-300">
                              Page {chunk.page_number}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => copyChunkText(text, index)}
                            className="inline-flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
                            title="Copy snippet"
                          >
                            {copiedIndex === index ? (
                              <span className="text-emerald-400 font-medium">✓ Copied</span>
                            ) : (
                              <span>Copy</span>
                            )}
                          </button>
                          <span className="text-zinc-700">·</span>
                          <button
                            type="button"
                            onClick={() => toggleChunk(index)}
                            className="text-[11px] font-medium text-accent-violet-light hover:text-accent-violet cursor-pointer"
                          >
                            {isExpanded ? "Collapse" : "Expand"}
                          </button>
                        </div>
                      </div>

                      {/* Chunk Content */}
                      <div className="relative">
                        <p
                          className={`text-xs text-zinc-300 leading-relaxed font-normal bg-zinc-900/80 p-2.5 rounded-lg border border-white/[0.04] selection:bg-accent-violet/30 ${
                            isExpanded ? "whitespace-pre-wrap max-h-96 overflow-y-auto" : "line-clamp-3"
                          }`}
                        >
                          {text}
                        </p>
                      </div>

                      <div className="mt-1.5 flex items-center justify-between text-[10px] text-zinc-500 font-mono">
                        <span>{text.length} characters · {wordCount} words</span>
                        {chunk.chunk_strategy && (
                          <span className="capitalize">{chunk.chunk_strategy.replace('_', ' ')}</span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </section>
      </div>
    </article>
  );
}
