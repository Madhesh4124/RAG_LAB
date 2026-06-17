import React, { useEffect, useState } from 'react';
import { deleteEvaluationReport, listEvaluationReports } from '../../services/api';

function formatMetric(value) {
  if (value === null || value === undefined) return "N/A";
  const num = Number(value);
  if (!Number.isFinite(num)) return "N/A";
  return num.toFixed(3);
}

function formatPercent(value) {
  if (value === null || value === undefined) return "N/A";
  const num = Number(value);
  if (!Number.isFinite(num)) return "N/A";
  const normalized = num <= 1 ? num * 100 : num;
  return `${normalized.toFixed(1)}%`;
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function MetricCard({ label, value, hint }) {
  const available = value !== null && value !== undefined && Number.isFinite(Number(value));
  return (
    <div className={`rounded-xl border p-3 ${available ? "border-gray-200 bg-gray-50" : "border-gray-100 bg-gray-50/60"}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{label}</p>
      <p className={`mt-1 font-mono text-lg ${available ? "text-gray-900" : "text-gray-400"}`}>{formatMetric(value)}</p>
      {hint ? <p className="mt-1 text-xs text-gray-500">{hint}</p> : null}
    </div>
  );
}

function formatReportMode(report, fastMode) {
  if (!report) return "";
  return fastMode ? "Fast score-only report" : "Deep judged report";
}

function SavedReportRow({ rec, onDelete }) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm("Delete this saved report?")) return;
    setDeleting(true);
    try {
      await deleteEvaluationReport(rec.id);
      onDelete(rec.id);
    } catch {
      alert("Failed to delete report.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-700 truncate">{rec.query || "(no query)"}</p>
          <p className="text-[11px] text-gray-400 mt-0.5">
            {rec.mode || "unknown"} · {formatDate(rec.created_at)}
          </p>
        </div>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="text-gray-400 hover:text-red-600 disabled:opacity-40 transition-colors p-1 shrink-0"
          title="Delete report"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>
      <div className="grid grid-cols-4 gap-1.5 text-center">
        {[
          ["Faith.", rec.faithfulness],
          ["Ans. Rel.", rec.answer_relevancy],
          ["Ctx Prec.", rec.context_precision],
          ["Ctx Rec.", rec.context_recall],
        ].map(([label, val]) => (
          <div key={label} className="rounded-lg bg-gray-50 border border-gray-100 py-1.5 px-1">
            <p className="text-[10px] text-gray-400 font-semibold uppercase">{label}</p>
            <p className={`font-mono text-sm mt-0.5 ${val !== null && val !== undefined && Number.isFinite(Number(val)) ? "text-gray-900" : "text-gray-300"}`}>
              {formatMetric(val)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function EvaluationPanel({ open, onClose, title, report, loading, error, selector, onRunDeepEvaluation, deepLoading = false }) {
  const [showSaved, setShowSaved] = useState(false);
  const [savedReports, setSavedReports] = useState([]);
  const [savedLoading, setSavedLoading] = useState(false);
  const [savedError, setSavedError] = useState("");

  const loadSavedReports = async () => {
    setSavedLoading(true);
    setSavedError("");
    try {
      const res = await listEvaluationReports({ limit: 20 });
      setSavedReports(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      setSavedError(err?.response?.data?.detail || err?.message || "Failed to load reports");
    } finally {
      setSavedLoading(false);
    }
  };

  useEffect(() => {
    if (showSaved) void loadSavedReports();
  }, [showSaved]);

  if (!open) return null;

  const retrieval = report?.retrieval_metrics || {};
  const answer = report?.answer_metrics || {};
  const judgments = Array.isArray(report?.chunk_judgments) ? report.chunk_judgments : [];
  const timingMs = Number(report?.timing_ms);
  const fastMode = report?.mode === "message-fast";
  const judgedMode = report && !fastMode;
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
                Click "Run Evaluation" to generate retrieval and answer metrics.
              </p>
              {report ? (
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                  <span className={`rounded-full px-2 py-0.5 font-medium ${summaryMode ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"}`}>
                    {summaryMode ? "Summary mode" : "Retrieval mode"}
                  </span>
                  <span className="text-gray-400">
                    {formatReportMode(report, fastMode)}{Number.isFinite(timingMs) ? ` in ${timingMs.toFixed(0)}ms` : ""}
                  </span>
                  <span className="text-gray-400">query routing: {queryMode}</span>
                </div>
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowSaved((v) => !v)}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:border-purple-200 hover:bg-purple-50 hover:text-purple-700"
              >
                {showSaved ? "Hide Saved" : "Saved Reports"}
              </button>
              {onRunDeepEvaluation ? (
                <button
                  type="button"
                  onClick={onRunDeepEvaluation}
                  disabled={deepLoading}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {deepLoading ? "Running..." : "Run Evaluation"}
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
          {/* ── Saved Reports Panel ── */}
          {showSaved && (
            <section className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-gray-900">Saved Reports</h3>
                <button
                  type="button"
                  onClick={() => void loadSavedReports()}
                  disabled={savedLoading}
                  className="text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50"
                >
                  {savedLoading ? "Loading..." : "Refresh"}
                </button>
              </div>
              {savedError && (
                <p className="text-xs text-red-600">{savedError}</p>
              )}
              {!savedLoading && savedReports.length === 0 && (
                <div className="rounded-xl border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-400 text-center">
                  No saved reports yet. Run an evaluation above to generate and save one.
                </div>
              )}
              <div className="space-y-2">
                {savedReports.map((rec) => (
                  <SavedReportRow
                    key={rec.id}
                    rec={rec}
                    onDelete={(id) => setSavedReports((prev) => prev.filter((r) => r.id !== id))}
                  />
                ))}
              </div>
            </section>
          )}

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

          {!loading && !error && !report ? (
            <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center text-sm text-gray-400">
              No evaluation report generated yet. Click "Run Evaluation" above to compute the metrics.
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
                      ? "Fast mode shows saved similarity scores. Run deep evaluation for LLM-judged relevance."
                      : "Deep mode uses LLM chunk judgments. Similarity score and judged relevance can disagree."}
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <MetricCard label="Precision@K" value={judgedMode ? retrieval.precision_at_k : null} hint={fastMode ? "Run deep evaluation for judged relevance." : null} />
                  <MetricCard label="Recall@K" value={judgedMode ? retrieval.recall_at_k : null} hint={fastMode ? "Run deep evaluation for judged relevance." : null} />
                  <MetricCard label="Hit Rate@K" value={judgedMode ? retrieval.hit_rate_at_k : null} hint={fastMode ? "Run deep evaluation for judged relevance." : null} />
                  <MetricCard label="Reciprocal Rank" value={judgedMode ? retrieval.reciprocal_rank : null} hint={fastMode ? "Run deep evaluation for judged relevance." : "MRR for a single query turn."} />
                  <MetricCard label="Average Precision" value={judgedMode ? retrieval.average_precision : null} hint={fastMode ? "Run deep evaluation for judged relevance." : null} />
                  <MetricCard label="nDCG@K" value={judgedMode ? retrieval.ndcg_at_k : null} hint={fastMode ? "Run deep evaluation for judged relevance." : null} />
                  <MetricCard label="Avg Similarity" value={retrieval.avg_similarity} hint="Mean retriever similarity, not a relevance verdict." />
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
                      {judgedMode
                        ? `LLM-judged relevant chunks: ${retrieval.relevant_retrieved ?? 0} / ${retrieval.evaluated_k ?? 0}`
                        : "Similarity scores only. Run deep evaluation for relevance judgments."}
                    </p>
                  </div>
                  {judgedMode ? (
                    <p className="text-xs text-gray-400">
                      Candidate pool: {retrieval.candidate_pool_size ?? 0}
                    </p>
                  ) : null}
                </div>
                <div className="space-y-3">
                  {judgments.map((item) => (
                    <div key={`${item.rank}-${item.text_preview}`} className="rounded-xl border border-gray-200 bg-white p-3">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-gray-400">#{item.rank}</span>
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${judgedMode ? (item.relevant ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700") : "bg-gray-100 text-gray-500"}`}>
                            {judgedMode ? (item.relevant ? "Judge: relevant" : "Judge: not relevant") : "Similarity only"}
                          </span>
                        </div>
                        <span className="text-xs font-mono text-gray-500">Similarity {formatPercent(item.score)}</span>
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
