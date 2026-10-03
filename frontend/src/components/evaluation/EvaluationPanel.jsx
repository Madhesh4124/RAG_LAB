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
    <div className={`rounded-xl border p-3.5 ${available ? "border-white/10 bg-surface-2/90" : "border-white/[0.06] bg-surface-2/40"}`}>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-[#ADACA7]">{label}</p>
      <p className={`mt-1 font-mono text-lg font-bold ${available ? "text-[#FCF8D8]" : "text-white/30"}`}>{formatMetric(value)}</p>
      {hint ? <p className="mt-1 text-[11px] text-[#D9DADF]/60 leading-tight">{hint}</p> : null}
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
    <div className="rounded-xl border border-white/10 bg-surface-2/80 p-3.5 space-y-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-[#FCF8D8] truncate">{rec.query || "(no query)"}</p>
          <p className="text-[10px] text-[#ADACA7] mt-0.5 font-mono">
            {rec.mode || "unknown"} · {formatDate(rec.created_at)}
          </p>
        </div>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="text-white/40 hover:text-red-400 disabled:opacity-40 transition-colors p-1 shrink-0"
          title="Delete report"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
          <div key={label} className="rounded-lg bg-surface-1 border border-white/[0.06] py-1.5 px-1">
            <p className="text-[9px] text-[#ADACA7] font-semibold uppercase">{label}</p>
            <p className={`font-mono text-xs mt-0.5 font-bold ${val !== null && val !== undefined && Number.isFinite(Number(val)) ? "text-[#FCF8D8]" : "text-white/30"}`}>
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
    <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm">
      <div className="h-full w-full max-w-2xl overflow-y-auto border-l border-white/10 bg-surface-1/95 shadow-2xl backdrop-blur-2xl">
        <div className="sticky top-0 z-10 border-b border-white/[0.08] bg-surface-1/90 px-6 py-5 backdrop-blur-xl">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-bold text-[#FCF8D8] tracking-tight">{title || "Evaluation"}</h2>
              <p className="mt-1 text-xs text-[#D9DADF]/70">
                Click "Run Evaluation" to generate retrieval and answer metrics.
              </p>
              {report ? (
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${summaryMode ? "bg-accent-violet/15 text-accent-violet-light border border-accent-violet/30" : "bg-[#7C7D75]/20 text-[#FCF8D8] border border-white/10"}`}>
                    {summaryMode ? "Summary mode" : "Retrieval mode"}
                  </span>
                  <span className="text-[#ADACA7] text-[11px]">
                    {formatReportMode(report, fastMode)}{Number.isFinite(timingMs) ? ` in ${timingMs.toFixed(0)}ms` : ""}
                  </span>
                  <span className="text-[#ADACA7] text-[11px] font-mono">routing: {queryMode}</span>
                </div>
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowSaved((v) => !v)}
                className="rounded-full border border-white/10 px-3.5 py-1.5 text-xs font-semibold text-[#D9DADF] hover:bg-white/[0.08] hover:border-white/20 transition-all"
              >
                {showSaved ? "Hide Saved" : "Saved Reports"}
              </button>
              {onRunDeepEvaluation ? (
                <button
                  type="button"
                  onClick={onRunDeepEvaluation}
                  disabled={deepLoading}
                  className="rounded-full px-4 py-1.5 text-xs font-bold bg-accent-violet text-white hover:bg-accent-violet-light shadow-[0_0_12px_rgba(221,112,11,0.35)] disabled:cursor-not-allowed disabled:opacity-40 transition-all"
                >
                  {deepLoading ? "Running..." : "Run Evaluation"}
                </button>
              ) : null}
              <button
                type="button"
                onClick={onClose}
                className="rounded-full px-2.5 py-1.5 text-xs font-semibold text-white/50 hover:text-white hover:bg-white/[0.06] transition-all"
              >
                Close
              </button>
            </div>
          </div>
          {selector ? <div className="mt-4">{selector}</div> : null}
        </div>

        <div className="space-y-6 px-6 py-6">
          {/* ── Saved Reports Panel ── */}
          {showSaved && (
            <section className="space-y-3">
              <div className="flex items-center justify-between gap-2 pb-2 border-b border-white/[0.06]">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Saved Reports</h3>
                <button
                  type="button"
                  onClick={() => void loadSavedReports()}
                  disabled={savedLoading}
                  className="text-xs text-accent-violet-light hover:underline disabled:opacity-50 font-semibold"
                >
                  {savedLoading ? "Loading..." : "Refresh"}
                </button>
              </div>
              {savedError && (
                <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 px-3 py-2 rounded-xl">{savedError}</p>
              )}
              {!savedLoading && savedReports.length === 0 && (
                <div className="rounded-xl border border-dashed border-white/10 px-4 py-6 text-xs text-white/50 text-center">
                  No saved reports yet. Run an evaluation above to generate and save one.
                </div>
              )}
              <div className="space-y-2.5">
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
            <div className="rounded-2xl border border-white/10 bg-surface-2/60 px-4 py-12 text-center text-sm text-[#FCF8D8] space-y-3">
              <div className="w-8 h-8 rounded-full border-2 border-white/10 border-t-accent-violet animate-spin mx-auto" />
              <p>Computing evaluation report…</p>
            </div>
          ) : null}

          {!loading && error ? (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-xs text-red-300">
              {error}
            </div>
          ) : null}

          {!loading && !error && !report ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-surface-2/40 px-6 py-10 text-center text-xs text-white/50 space-y-2">
              <p className="text-sm font-semibold text-[#FCF8D8]">No evaluation report generated yet</p>
              <p className="text-xs text-[#D9DADF]/60">Click "Run Evaluation" above to compute retrieval, faithfulness, and answer relevancy metrics.</p>
            </div>
          ) : null}

          {!loading && !error && report ? (
            <>
              <section className="space-y-3">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Retrieval Metrics</h3>
                  <p className="text-xs text-[#D9DADF]/70 mt-1">
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
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Answer Quality</h3>
                  <p className="text-xs text-[#D9DADF]/70 mt-1">
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
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Chunk Judgments</h3>
                    <p className="text-xs text-[#D9DADF]/70 mt-1">
                      {judgedMode
                        ? `LLM-judged relevant chunks: ${retrieval.relevant_retrieved ?? 0} / ${retrieval.evaluated_k ?? 0}`
                        : "Similarity scores only. Run deep evaluation for relevance judgments."}
                    </p>
                  </div>
                  {judgedMode ? (
                    <p className="text-xs text-[#ADACA7] font-mono">
                      Candidate pool: {retrieval.candidate_pool_size ?? 0}
                    </p>
                  ) : null}
                </div>
                <div className="space-y-3">
                  {judgments.map((item) => (
                    <div key={`${item.rank}-${item.text_preview}`} className="rounded-xl border border-white/10 bg-surface-2/80 p-4 space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-[#ADACA7]">#{item.rank}</span>
                          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${judgedMode ? (item.relevant ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" : "bg-red-500/15 text-red-400 border border-red-500/30") : "bg-white/[0.06] text-white/50 border border-white/10"}`}>
                            {judgedMode ? (item.relevant ? "Judge: relevant" : "Judge: not relevant") : "Similarity only"}
                          </span>
                        </div>
                        <span className="text-xs font-mono text-[#FCF8D8]">Similarity {formatPercent(item.score)}</span>
                      </div>
                      <p className="text-xs leading-relaxed text-[#D9DADF]">{item.text_preview}</p>
                    </div>
                  ))}
                  {!judgments.length ? (
                    <div className="rounded-xl border border-dashed border-white/10 px-4 py-6 text-xs text-white/50 text-center">
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
