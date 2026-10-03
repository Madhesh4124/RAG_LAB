import React, { useMemo } from 'react';
import { Badge, ProgressBar } from "../common/index";

function formatScore(val, decimals = 3) {
  if (val === null || val === undefined) return "N/A";
  const num = Number(val);
  if (!Number.isFinite(num)) return "N/A";
  return num.toFixed(decimals);
}

function formatPercent(val) {
  if (val === null || val === undefined) return "N/A";
  const num = Number(val);
  if (!Number.isFinite(num)) return "N/A";
  const normalized = num <= 1 ? num * 100 : num;
  return `${normalized.toFixed(1)}%`;
}

export default function CompareEvaluationTab({ results, onOpenEvaluationDetail }) {
  if (!results || results.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-white/10 bg-surface-1/40 p-8 text-center text-sm text-zinc-400">
        Run a comparison query to view evaluation metrics side-by-side.
      </div>
    );
  }

  // Calculate best performer for key dimensions
  const highlights = useMemo(() => {
    let bestFaithfulness = { config: null, val: -1 };
    let bestRelevancy = { config: null, val: -1 };
    let fastestLatency = { config: null, val: Infinity };
    let bestPrecision = { config: null, val: -1 };

    results.forEach((r) => {
      const name = r.config?.name || "Config";
      const faith = r.evaluation?.answer_metrics?.faithfulness;
      if (faith != null && faith > bestFaithfulness.val) {
        bestFaithfulness = { config: name, val: faith };
      }

      const rel = r.evaluation?.answer_metrics?.answer_relevancy;
      if (rel != null && rel > bestRelevancy.val) {
        bestRelevancy = { config: name, val: rel };
      }

      const lat = Number(r.latency_ms ?? 0);
      if (lat > 0 && lat < fastestLatency.val) {
        fastestLatency = { config: name, val: lat };
      }

      const prec = r.evaluation?.retrieval_metrics?.precision_at_k;
      if (prec != null && prec > bestPrecision.val) {
        bestPrecision = { config: name, val: prec };
      }
    });

    return {
      bestFaithfulness: bestFaithfulness.config ? bestFaithfulness : null,
      bestRelevancy: bestRelevancy.config ? bestRelevancy : null,
      fastestLatency: fastestLatency.config ? fastestLatency : null,
      bestPrecision: bestPrecision.config ? bestPrecision : null,
    };
  }, [results]);

  const maxLatency = Math.max(...results.map((r) => Number(r.latency_ms || 1)), 1);

  return (
    <div className="space-y-6">
      {/* ── Top Winners / Highlights ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* Groundedness Card */}
        <div className="rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-emerald-950/30 to-zinc-900/60 p-4 shadow-lg backdrop-blur-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-emerald-400 uppercase tracking-wide">
            <span>🛡️ Groundedness</span>
            {highlights.bestFaithfulness && (
              <span className="rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 text-[10px]">
                Leader
              </span>
            )}
          </div>
          <p className="mt-2 text-xl font-bold text-zinc-100">
            {highlights.bestFaithfulness ? formatPercent(highlights.bestFaithfulness.val) : "Pending"}
          </p>
          <p className="mt-1 text-xs text-zinc-400 truncate">
            {highlights.bestFaithfulness ? highlights.bestFaithfulness.config : "No evaluation run"}
          </p>
        </div>

        {/* Answer Relevancy Card */}
        <div className="rounded-2xl border border-blue-500/20 bg-gradient-to-br from-blue-950/30 to-zinc-900/60 p-4 shadow-lg backdrop-blur-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-blue-400 uppercase tracking-wide">
            <span>🎯 Answer Relevancy</span>
            {highlights.bestRelevancy && (
              <span className="rounded bg-blue-500/15 text-blue-300 border border-blue-500/30 px-1.5 py-0.5 text-[10px]">
                Leader
              </span>
            )}
          </div>
          <p className="mt-2 text-xl font-bold text-zinc-100">
            {highlights.bestRelevancy ? formatPercent(highlights.bestRelevancy.val) : "Pending"}
          </p>
          <p className="mt-1 text-xs text-zinc-400 truncate">
            {highlights.bestRelevancy ? highlights.bestRelevancy.config : "No evaluation run"}
          </p>
        </div>

        {/* Precision Card */}
        <div className="rounded-2xl border border-purple-500/20 bg-gradient-to-br from-purple-950/30 to-zinc-900/60 p-4 shadow-lg backdrop-blur-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-purple-400 uppercase tracking-wide">
            <span>🔍 Context Precision</span>
            {highlights.bestPrecision && (
              <span className="rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 px-1.5 py-0.5 text-[10px]">
                Leader
              </span>
            )}
          </div>
          <p className="mt-2 text-xl font-bold text-zinc-100">
            {highlights.bestPrecision ? formatScore(highlights.bestPrecision.val) : "Pending"}
          </p>
          <p className="mt-1 text-xs text-zinc-400 truncate">
            {highlights.bestPrecision ? highlights.bestPrecision.config : "No evaluation run"}
          </p>
        </div>

        {/* Latency Card */}
        <div className="rounded-2xl border border-amber-500/20 bg-gradient-to-br from-amber-950/30 to-zinc-900/60 p-4 shadow-lg backdrop-blur-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-amber-400 uppercase tracking-wide">
            <span>⚡ Fastest Latency</span>
            {highlights.fastestLatency && (
              <span className="rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 text-[10px]">
                Fastest
              </span>
            )}
          </div>
          <p className="mt-2 text-xl font-bold text-zinc-100">
            {highlights.fastestLatency ? `${Math.round(highlights.fastestLatency.val)}ms` : "N/A"}
          </p>
          <p className="mt-1 text-xs text-zinc-400 truncate">
            {highlights.fastestLatency ? highlights.fastestLatency.config : "-"}
          </p>
        </div>
      </div>

      {/* ── Side-by-Side Evaluation Matrix Table ── */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-zinc-900/70 backdrop-blur-md shadow-xl">
        <div className="border-b border-white/[0.08] bg-zinc-950/60 px-5 py-3.5 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-zinc-100">Comparative Metrics Matrix</h3>
            <p className="text-xs text-zinc-400">Benchmark comparison of all staged configurations on this prompt.</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/[0.08] bg-zinc-950/80 text-zinc-400 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4 w-52">Metric</th>
                {results.map((r, i) => (
                  <th key={r.config?.name || i} className="py-3 px-4 min-w-[200px]">
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-zinc-100 font-bold normal-case text-sm truncate">
                        {r.config?.name}
                      </span>
                      <button
                        type="button"
                        onClick={() => onOpenEvaluationDetail?.(r)}
                        className="text-[11px] font-medium text-accent-violet-light hover:text-accent-violet underline normal-case transition-colors cursor-pointer"
                      >
                        Deep View
                      </button>
                    </div>
                    <div className="mt-1.5 flex flex-wrap gap-1.5 font-normal text-[10px] text-zinc-400 normal-case">
                      <span className="rounded bg-white/[0.06] border border-white/[0.06] px-1.5 py-0.5 text-zinc-300">
                        {r.config?.chunk_strategy}
                      </span>
                      <span className="rounded bg-white/[0.06] border border-white/[0.06] px-1.5 py-0.5 text-zinc-300">
                        k={r.config?.top_k}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06] text-zinc-300">
              {/* ── Generation Quality Section ── */}
              <tr className="bg-white/[0.02]">
                <td colSpan={results.length + 1} className="py-2.5 px-4 font-semibold text-[11px] text-zinc-400 uppercase tracking-wide">
                  Generation Quality (LLM Evaluated)
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-medium text-zinc-200">
                  <div>Faithfulness</div>
                  <div className="text-[10px] text-zinc-500 font-normal">Grounded in retrieved chunks without hallucinations</div>
                </td>
                {results.map((r, i) => {
                  const val = r.evaluation?.answer_metrics?.faithfulness;
                  const isLeader = highlights.bestFaithfulness?.config === r.config?.name && val != null;
                  return (
                    <td key={i} className={`py-3 px-4 ${isLeader ? "bg-emerald-500/10 font-semibold" : ""}`}>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className={`font-mono ${isLeader ? "text-emerald-400 font-bold" : "text-zinc-100"}`}>
                          {val != null ? formatPercent(val) : "N/A"}
                        </span>
                        {isLeader && <Badge color="green">Best</Badge>}
                      </div>
                      {val != null && <ProgressBar value={val * 100} max={100} color={val > 0.7 ? "green" : "blue"} />}
                    </td>
                  );
                })}
              </tr>

              <tr>
                <td className="py-3 px-4 font-medium text-zinc-200">
                  <div>Answer Relevancy</div>
                  <div className="text-[10px] text-zinc-500 font-normal">How directly the response answers user question</div>
                </td>
                {results.map((r, i) => {
                  const val = r.evaluation?.answer_metrics?.answer_relevancy;
                  const isLeader = highlights.bestRelevancy?.config === r.config?.name && val != null;
                  return (
                    <td key={i} className={`py-3 px-4 ${isLeader ? "bg-blue-500/10 font-semibold" : ""}`}>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className={`font-mono ${isLeader ? "text-blue-400 font-bold" : "text-zinc-100"}`}>
                          {val != null ? formatPercent(val) : "N/A"}
                        </span>
                        {isLeader && <Badge color="blue">Best</Badge>}
                      </div>
                      {val != null && <ProgressBar value={val * 100} max={100} color="blue" />}
                    </td>
                  );
                })}
              </tr>

              <tr>
                <td className="py-3 px-4 font-medium text-zinc-200">
                  <div>Context Recall</div>
                  <div className="text-[10px] text-zinc-500 font-normal">Extent to which retrieved context covers required info</div>
                </td>
                {results.map((r, i) => {
                  const val = r.evaluation?.answer_metrics?.context_recall;
                  return (
                    <td key={i} className="py-3 px-4">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-mono text-zinc-100">
                          {val != null ? formatPercent(val) : "N/A"}
                        </span>
                      </div>
                      {val != null && <ProgressBar value={val * 100} max={100} color="orange" />}
                    </td>
                  );
                })}
              </tr>

              {/* ── Retrieval Performance Section ── */}
              <tr className="bg-white/[0.02]">
                <td colSpan={results.length + 1} className="py-2.5 px-4 font-semibold text-[11px] text-zinc-400 uppercase tracking-wide">
                  Retrieval Performance
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-medium text-zinc-200">
                  <div>Context Precision@K</div>
                  <div className="text-[10px] text-zinc-500 font-normal">Proportion of retrieved chunks judged relevant</div>
                </td>
                {results.map((r, i) => {
                  const val = r.evaluation?.retrieval_metrics?.precision_at_k;
                  const isLeader = highlights.bestPrecision?.config === r.config?.name && val != null;
                  return (
                    <td key={i} className={`py-3 px-4 ${isLeader ? "bg-purple-500/10 font-semibold" : ""}`}>
                      <div className="flex items-center justify-between">
                        <span className={`font-mono ${isLeader ? "text-purple-400 font-bold" : "text-zinc-100"}`}>
                          {formatScore(val)}
                        </span>
                        {isLeader && <Badge color="purple">Top</Badge>}
                      </div>
                    </td>
                  );
                })}
              </tr>

              <tr>
                <td className="py-3 px-4 font-medium text-zinc-200">
                  <div>Hit Rate@K</div>
                  <div className="text-[10px] text-zinc-500 font-normal">1.0 if at least one relevant chunk was found</div>
                </td>
                {results.map((r, i) => {
                  const val = r.evaluation?.retrieval_metrics?.hit_rate_at_k;
                  return (
                    <td key={i} className="py-3 px-4 font-mono text-zinc-100">
                      {val != null ? (val > 0 ? "1.000 (Hit ✓)" : "0.000 (Miss ✗)") : "N/A"}
                    </td>
                  );
                })}
              </tr>

              <tr>
                <td className="py-3 px-4 font-medium text-zinc-200">
                  <div>Average Similarity Score</div>
                  <div className="text-[10px] text-zinc-500 font-normal">Mean vector distance similarity of top matches</div>
                </td>
                {results.map((r, i) => (
                  <td key={i} className="py-3 px-4 font-mono text-zinc-100">
                    {formatScore(r.avg_similarity, 4)}
                  </td>
                ))}
              </tr>

              <tr>
                <td className="py-3 px-4 font-medium text-zinc-200">
                  <div>Chunks Retrieved</div>
                  <div className="text-[10px] text-zinc-500 font-normal">Number of chunks returned matching threshold</div>
                </td>
                {results.map((r, i) => (
                  <td key={i} className="py-3 px-4 font-mono text-zinc-100">
                    {r.chunk_count} / {r.config?.top_k} max
                  </td>
                ))}
              </tr>

              {/* ── System Efficiency Section ── */}
              <tr className="bg-white/[0.02]">
                <td colSpan={results.length + 1} className="py-2.5 px-4 font-semibold text-[11px] text-zinc-400 uppercase tracking-wide">
                  Speed & Efficiency
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-medium text-zinc-200">
                  <div>Response Latency</div>
                  <div className="text-[10px] text-zinc-500 font-normal">Total retrieval & generation time (ms)</div>
                </td>
                {results.map((r, i) => {
                  const lat = Math.round(Number(r.latency_ms ?? 0));
                  const isFastest = highlights.fastestLatency?.config === r.config?.name;
                  const pct = Math.round((lat / maxLatency) * 100);
                  return (
                    <td key={i} className={`py-3 px-4 ${isFastest ? "bg-amber-500/10 font-semibold" : ""}`}>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className={`font-mono ${isFastest ? "text-amber-400 font-bold" : "text-zinc-100"}`}>
                          {lat}ms
                        </span>
                        {isFastest && <Badge color="yellow">Fastest</Badge>}
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isFastest ? "bg-amber-400" : "bg-zinc-600"}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </td>
                  );
                })}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Retrieved Chunks Relevance Breakdown ── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-100">Retrieved Chunks Relevance Judgments</h3>
          <p className="text-xs text-zinc-500">Evaluation breakdown per chunk</p>
        </div>

        <div className="grid gap-4 grid-cols-1 md:grid-flow-col md:auto-cols-[minmax(320px,1fr)] overflow-x-auto pb-2">
          {results.map((r) => {
            const judgments = r.evaluation?.chunk_judgments || [];
            const chunksList = r.chunk_details || (r.chunks || []).map((t, idx) => ({
              index: idx + 1,
              text: t,
              score: r.scores?.[idx] ?? 0,
            }));

            return (
              <div key={r.config?.name} className="rounded-xl border border-white/10 bg-zinc-900/60 p-4 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-2">
                  <h4 className="font-semibold text-zinc-200 text-sm">{r.config?.name}</h4>
                  <span className="text-xs text-zinc-400 font-mono">{chunksList.length} chunks</span>
                </div>

                {chunksList.length === 0 ? (
                  <p className="text-xs text-zinc-500 italic py-2">No chunks retrieved.</p>
                ) : (
                  <div className="space-y-2.5">
                    {chunksList.map((chunk, idx) => {
                      const judgment = judgments[idx];
                      const isRelevant = judgment ? judgment.relevant : true;
                      const score = Number(chunk.score ?? r.scores?.[idx] ?? 0);
                      const text = chunk.text || "";

                      return (
                        <div key={idx} className="rounded-lg border border-white/[0.06] bg-zinc-950/60 p-2.5 text-xs space-y-1.5">
                          <div className="flex items-center justify-between gap-1">
                            <span className="font-semibold text-zinc-300">Rank #{idx + 1}</span>
                            <div className="flex items-center gap-1.5">
                              <Badge color={isRelevant ? "green" : "gray"}>
                                {isRelevant ? "Relevant ✓" : "Irrelevant ✗"}
                              </Badge>
                              <span className="font-mono text-[10px] text-zinc-400">
                                {score.toFixed(4)}
                              </span>
                            </div>
                          </div>

                          <p className="line-clamp-2 text-zinc-300 text-[11px] leading-relaxed">
                            {text}
                          </p>

                          {chunk.page_number && (
                            <span className="inline-block text-[10px] text-purple-400 font-medium">
                              Page {chunk.page_number}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
