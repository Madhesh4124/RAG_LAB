import React from 'react';
import ResultCard from "./ResultCard";

export default function ResultsGrid({ results, isLoading }) {
  if (isLoading) return null;

  if (!results || results.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-gray-200 bg-white px-4 py-10 text-center text-sm text-gray-400 shadow-sm">
        Results will appear here after you run a comparison.
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <style>{`
        @keyframes compareFadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Results</h2>
          <p className="text-sm text-gray-500">Side-by-side output for each staged config.</p>
        </div>
      </div>

      <div className="overflow-x-auto pb-2">
        <div className="grid gap-4 grid-cols-1 md:grid-flow-col md:auto-cols-[minmax(320px,1fr)]">
          {results.map((result) => (
            <div key={result.config?.name} style={{ animation: "compareFadeIn 0.35s ease both" }}>
              <ResultCard result={result} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
