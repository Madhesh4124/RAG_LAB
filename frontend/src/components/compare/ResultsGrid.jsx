import React, { useState } from 'react';
import ResultCard from "./ResultCard";
import CompareEvaluationTab from "./CompareEvaluationTab";
import EvaluationPanel from "../evaluation/EvaluationPanel";

export default function ResultsGrid({ results, isLoading }) {
  const [selectedResult, setSelectedResult] = useState(null);
  const [activeTab, setActiveTab] = useState("responses");

  if (isLoading) return null;

  if (!results || results.length === 0) {
    return (
      <div className="p-1.5 rounded-[2rem] bg-white/[0.03] border border-dashed border-white/[0.15] reveal">
        <div className="rounded-[calc(2rem-0.375rem)] bg-surface-1 px-6 py-12 text-center
          shadow-[inset_0_1px_1px_rgba(255,255,255,0.04)]">
          <div className="mx-auto mb-4 w-12 h-12 rounded-2xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-white/40">
              <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
            </svg>
          </div>
          <p className="text-sm text-white/60 font-medium">Results will appear here after you run a comparison.</p>
        </div>
      </div>
    );
  }

  const hasEvaluation = results.some((r) => r.evaluation != null);

  return (
    <>
      <section className="space-y-4">
        {/* Header with Title and Tabs */}
        <div className="p-1.5 rounded-[2rem] bg-white/[0.04] border border-white/[0.16] reveal">
          <div className="rounded-[calc(2rem-0.375rem)] bg-surface-1 px-5 py-4
            shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <p className="text-[10px] uppercase tracking-[0.15em] font-semibold text-white/60 mb-1">Results</p>
                <h2 className="text-base font-bold text-white">Compare Results</h2>
                <p className="text-sm text-white/65 mt-0.5">
                  {activeTab === "responses"
                    ? "Side-by-side answers and retrieved chunks for each staged config."
                    : "Side-by-side evaluation metrics, groundedness, and retrieval precision."}
                </p>
              </div>

              {/* Tab toggle */}
              <div className="flex items-center p-1 rounded-2xl bg-white/[0.04] border border-white/[0.06] self-start sm:self-auto">
                <button type="button" onClick={() => setActiveTab("responses")}
                  className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold
                    transition-all duration-400 ease-[cubic-bezier(0.32,0.72,0,1)]
                    ${activeTab === "responses"
                      ? "bg-white/[0.10] text-white shadow-[inset_0_1px_1px_rgba(255,255,255,0.10)]"
                      : "text-white/60 hover:text-white/60"}`}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="18" height="18" x="3" y="3" rx="2" /><path d="M12 3v18" />
                  </svg>
                  Responses
                </button>
                <button type="button" onClick={() => setActiveTab("evaluation")}
                  className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold
                    transition-all duration-400 ease-[cubic-bezier(0.32,0.72,0,1)]
                    ${activeTab === "evaluation"
                      ? "bg-white/[0.10] text-white shadow-[inset_0_1px_1px_rgba(255,255,255,0.10)]"
                      : "text-white/60 hover:text-white/60"}`}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 20v-6M6 20V10M18 20V4" />
                  </svg>
                  Evaluation
                  {hasEvaluation && (
                    <span className="h-1.5 w-1.5 rounded-full bg-accent-emerald-light"></span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Tab 1: Responses & Chunks Grid */}
        {activeTab === "responses" && (
          <div className="overflow-x-auto pb-2 animate-fade-up">
            <div className="grid gap-4 grid-cols-1 md:grid-flow-col md:auto-cols-[minmax(320px,1fr)]">
              {results.map((result) => (
                <div key={result.config?.name}>
                  <ResultCard result={result} onOpenEvaluation={setSelectedResult} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 2: Evaluation Comparison Matrix */}
        {activeTab === "evaluation" && (
          <div className="animate-fade-up">
            <CompareEvaluationTab results={results} onOpenEvaluationDetail={setSelectedResult} />
          </div>
        )}
      </section>

      <EvaluationPanel
        open={Boolean(selectedResult)}
        onClose={() => setSelectedResult(null)}
        title={selectedResult ? `${selectedResult.config?.name || "Compare"} Evaluation` : "Compare Evaluation"}
        report={selectedResult?.evaluation || null}
        loading={false}
        error={!selectedResult?.evaluation && selectedResult ? "Evaluation data was not available for this result." : ""}
      />
    </>
  );
}
