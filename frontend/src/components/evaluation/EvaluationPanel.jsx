import React from 'react';

function formatMetric(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "N/A";
  return num.toFixed(3);
}

function formatPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "N/A";
  const normalized = num <= 1 ? num * 100 : num;
  return `${normalized.toFixed(1)}%`;
}

function MetricCard({ label, value, hint }) {
  const available = Number.isFinite(Number(value));
  return (
    <div className={`rounded-xl border p-3 ${available ? "border-gray-200 bg-gray-50" : "border-gray-100 bg-gray-50/60"}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{label}</p>
      <p className={`mt-1 font-mono text-lg ${available ? "text-gray-900" : "text-gray-400"}`}>{formatMetric(value)}</p>
      {hint ? <p className="mt-1 text-xs text-gray-500">{hint}</p> : null}
    </div>
  );
}

export default function EvaluationPanel({ open, onClose, title, report, loading, error, selector, onRunDeepEvaluation, deepLoading = false }) {
  if (!open) return null;

  const retrieval = report?.retrieval_metrics || {};
  const answer = report?.answer_metrics || {};
  const judgments = Array.isArray(report?.chunk_judgments) ? report.chunk_judgments : [];
  const timingMs = Number(report?.timing_ms);
  const fastMode = report?.mode === "message-fast";
  const queryMode = report?.query_mode || "unknown";
  const summaryMode = Boolean(report?.summary_mode);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-gray-900/30 backdrop-blur-sm">
      <div className="h-full w-full max-w-2xl overflow-y-auto border-l border-gray-200 bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-gray-200 bg-white/95 px-5 py-4 backdrop-blur">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{title || "Evaluation"}</h2>
              <p className="mt-1 text-sm text-gray-500">
                Retrieval metrics stay hidden until you open this panel.
              </p>
              {report ? (
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                  <span className={`rounded-full px-2 py-0.5 font-medium ${summaryMode ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"}`}>
                    {summaryMode ? "Summary mode" : "Retrieval mode"}
                  </span>
                  <span className="text-gray-400">
                    {fastMode ? "Fast report" : "Detailed report"}{Number.isFinite(timingMs) ? ` in ${timingMs.toFixed(0)}ms` : ""}
                  </span>
                  <span className="text-gray-400">query routing: {queryMode}</span>
                </div>
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              {onRunDeepEvaluation ? (
                <button
                  type="button"
                  onClick={onRunDeepEvaluation}
                  disabled={deepLoading}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {deepLoading ? "Running..." : "Run Deep Evaluation"}
                </button>
              ) : null}
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700"
              >
                Close
              </button>
            </div>
          </div>
          {selector ? <div className="mt-4">{selector}</div> : null}
        </div>

        <div className="space-y-6 px-5 py-5">
          {loading ? (
            <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
              Computing evaluation report...
            </div>
          ) : null}

          {!loading && error ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          {!loading && !error && report ? (
            <>
              <section className="space-y-3">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">Retrieval Metrics</h3>
                  <p className="text-xs text-gray-500">
                    {summaryMode
                      ? "This turn was routed to summary mode, so these metrics only reflect how well the saved context supported a document overview."
                      : fastMode
                      ? "Fast mode uses saved retrieved chunks and cached answer scores for a quick health check."
                      : "`recall@k` is estimated against a judged candidate pool, not a hand-labeled benchmark set."}
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <MetricCard label="Precision@K" value={retrieval.precision_at_k} />
                  <MetricCard label="Recall@K" value={retrieval.recall_at_k} />
                  <MetricCard label="Hit Rate@K" value={retrieval.hit_rate_at_k} />
                  <MetricCard label="Reciprocal Rank" value={retrieval.reciprocal_rank} hint="MRR for a single query turn." />
                  <MetricCard label="Average Precision" value={retrieval.average_precision} />
                  <MetricCard label="nDCG@K" value={retrieval.ndcg_at_k} />
                  <MetricCard label="Avg Similarity" value={retrieval.avg_similarity} />
                  <MetricCard label="Diversity" value={retrieval.diversity_score} hint="Higher means less redundant chunks." />
                  <MetricCard label="MMR Lambda" value={retrieval.mmr_lambda} hint={retrieval.retrieval_strategy === "mmr" ? "Active MMR tradeoff value." : "Shown when the retriever uses MMR."} />
                </div>
              </section>

              <section className="space-y-3">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">Answer Quality</h3>
                  <p className="text-xs text-gray-500">
                    Unavailable metrics stay gray until cached scores exist or you run deep evaluation.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <MetricCard label="Faithfulness" value={answer.faithfulness} />
                  <MetricCard label="Answer Relevancy" value={answer.answer_relevancy} />
                  <MetricCard label="Context Precision" value={answer.context_precision} />
                  <MetricCard label="Context Recall" value={answer.context_recall} />
                </div>
              </section>

              <section className="space-y-3">
                <div className="flex items-end justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">Chunk Judgments</h3>
                    <p className="text-xs text-gray-500">
                      Relevant retrieved chunks: {retrieval.relevant_retrieved ?? 0} / {retrieval.evaluated_k ?? 0}
                    </p>
                  </div>
                  <p className="text-xs text-gray-400">
                    Candidate pool: {retrieval.candidate_pool_size ?? 0}
                  </p>
                </div>
                <div className="space-y-3">
                  {judgments.map((item) => (
                    <div key={`${item.rank}-${item.text_preview}`} className="rounded-xl border border-gray-200 bg-white p-3">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-gray-400">#{item.rank}</span>
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${item.relevant ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
                            {item.relevant ? "Relevant" : "Not relevant"}
                          </span>
                        </div>
                        <span className="text-xs font-mono text-gray-500">{formatPercent(item.score)}</span>
                      </div>
                      <p className="text-sm leading-relaxed text-gray-700">{item.text_preview}</p>
                    </div>
                  ))}
                  {!judgments.length ? (
                    <div className="rounded-xl border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-400">
                      No retrieved chunks were available to evaluate.
                    </div>
                  ) : null}
                </div>
              </section>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
