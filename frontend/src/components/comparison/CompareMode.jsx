import React from 'react';
import { useState } from "react";
import { compareConfigs, MOCK_COMPARE_RESULTS } from "../../services/api";
import ConfigCard from "./ConfigCard";
import { Button, Spinner } from "../common/index";

export default function CompareMode({ documentId }) {
  const [query,   setQuery]   = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const [configs, setConfigs] = useState([
    { name: "Broad Recall", top_k: 8, threshold: 0.3 },
    { name: "Precision Focus", top_k: 3, threshold: 0.7 },
    { name: "Balanced", top_k: 5, threshold: 0.5 },
  ]);

  const updateConfig = (idx, patch) => {
    setConfigs((prev) => prev.map((item, i) => (i === idx ? { ...item, ...patch } : item)));
  };

  const handleRun = async () => {
    if (!query.trim() || !documentId) return;
    setLoading(true);
    setError(null);
    try {
      const payload = {
        query,
        configs: configs.map((cfg) => ({
          name: cfg.name,
          top_k: Number(cfg.top_k),
          threshold: Number(cfg.threshold),
        })),
      };
      const { data } = await compareConfigs(payload);
      setResults(Array.isArray(data?.results) ? data.results : []);
    } catch (e) {
      console.error(e);
      setError(e.response?.data?.detail || e.message || "Failed to compare configurations.");
      setResults(MOCK_COMPARE_RESULTS);
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
        <span className="font-semibold">🔒 Controlled variables:</span> Active dataset, chunking, and embeddings are locked. Only top-k and threshold vary.
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
        <p className="text-sm font-semibold text-gray-800">Retrieval Configurations</p>
        <div className="grid gap-3 md:grid-cols-3">
          {configs.map((cfg, idx) => (
            <div key={cfg.name} className="rounded-lg border border-gray-200 p-3 space-y-2">
              <p className="text-sm font-medium text-gray-700">{cfg.name}</p>
              <label className="block text-xs text-gray-500">
                top_k
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={cfg.top_k}
                  onChange={(e) => updateConfig(idx, { top_k: e.target.value })}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1 text-sm"
                />
              </label>
              <label className="block text-xs text-gray-500">
                threshold
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={cfg.threshold}
                  onChange={(e) => updateConfig(idx, { threshold: e.target.value })}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1 text-sm"
                />
              </label>
            </div>
          ))}
        </div>
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
              <ConfigCard key={result.config?.name} result={result} />
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
  const formatMs = (value) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return "0ms";
    return `${Math.round(n)}ms`;
  };

  const metrics = [
    { key: "latency_ms", label: "Response Time",    format: formatMs,                  best: "min" },
    { key: "chunk_count", label: "Chunks Retrieved", format: (v) => Number(v ?? 0),     best: null  },
    { key: "avg_similarity", label: "Avg Similarity", format: (v) => Number(v ?? 0).toFixed(4), best: "max" },
  ];

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Metric</th>
            {results.map((r) => (
              <th key={r.config?.name} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">
                {r.config?.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {metrics.map(({ key, label, format, best }) => {
            const values = results.map((r) => Number(r[key] ?? 0));
            const bestVal = best === "min" ? Math.min(...values) : best === "max" ? Math.max(...values) : null;
            return (
              <tr key={key} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-600 font-medium">{label}</td>
                {results.map((r) => {
                  const v = Number(r[key] ?? 0);
                  const isBest = bestVal !== null && v === bestVal;
                  return (
                    <td key={`${r.config?.name}-${key}`} className={`px-4 py-3 font-mono ${isBest ? "text-green-600 font-semibold" : "text-gray-700"}`}>
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