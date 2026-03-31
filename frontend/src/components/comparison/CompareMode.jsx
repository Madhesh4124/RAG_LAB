import { useState } from "react";
import { compareConfigs } from "../../services/api";
import ConfigCard from "./ConfigCard";
import { Button, Spinner } from "../common/index";

export default function CompareMode({ documentId }) {
  const [query,   setQuery]   = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const handleRun = async () => {
    const handleRun = async () => {
  if (!query.trim()) return;
  setLoading(true);
  try {
    await new Promise((r) => setTimeout(r, 1200));
    setResults(MOCK_COMPARE_RESULTS);
  } catch (e) {
    console.error(e);
  } finally {
    setLoading(false);
  }
};
  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Compare Mode</h1>
        <p className="text-gray-400 text-sm mt-1">
          Run the same query across multiple configurations side-by-side.
        </p>
      </div>

      <div className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleRun()}
          placeholder="Ask a question about your document…"
          className="flex-1 rounded-lg border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <Button onClick={handleRun} disabled={!query.trim() || !documentId || loading}>
          {loading ? "Running…" : "Run Comparison"}
        </Button>
      </div>

      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-2 text-xs text-amber-700">
        <span className="font-semibold">🔒 Controlled variables:</span> Same LLM, temperature, max context. Only chunking strategy, embedding model, and top-k vary.
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          <p className="font-semibold">Error running comparison:</p>
          <p>{error}</p>
        </div>
      )}

      {loading && <Spinner label="Running pipeline across all configurations…" />}

      {results && results.length > 0 && !loading && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            {results.map((result) => (
              <ConfigCard key={result.configId} result={result} />
            ))}
          </div>
          <MetricsTable results={results} />
        </>
      )}

      {results && results.length === 0 && !loading && !error && (
        <div className="rounded-lg border-2 border-dashed border-gray-200 p-8 text-center text-gray-400">
          <p className="text-sm">No configurations found. Create a configuration in the Setup page first.</p>
        </div>
      )}
    </div>
  );
}

function MetricsTable({ results }) {
  const metrics = [
    { key: "response_time_ms", label: "Response Time",    format: (v) => `${v}ms`,     best: "min" },
    { key: "chunks_retrieved", label: "Chunks Retrieved", format: (v) => v,             best: null  },
    { key: "avg_similarity",   label: "Avg Similarity",   format: (v) => v.toFixed(2),  best: "max" },
    { key: "token_count",      label: "Tokens Used",      format: (v) => v,             best: "min" },
  ];

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Metric</th>
            {results.map((r) => (
              <th key={r.configId} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">
                {r.configName}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {metrics.map(({ key, label, format, best }) => {
            const values = results.map((r) => r.metrics[key]);
            const bestVal = best === "min" ? Math.min(...values) : best === "max" ? Math.max(...values) : null;
            return (
              <tr key={key} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-600 font-medium">{label}</td>
                {results.map((r) => {
                  const v = r.metrics[key];
                  const isBest = bestVal !== null && v === bestVal;
                  return (
                    <td key={r.configId} className={`px-4 py-3 font-mono ${isBest ? "text-green-600 font-semibold" : "text-gray-700"}`}>
                      {format(v)} {isBest && "✓"}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}