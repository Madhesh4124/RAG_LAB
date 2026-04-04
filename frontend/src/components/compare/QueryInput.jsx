import React from 'react';
import { Button } from "../common/index";

export default function QueryInput({ query, onChange, onRun, isLoading, isDisabled, stagedCount, isActivated }) {
  const canRun = query.trim().length > 0 && stagedCount >= 1 && !isLoading && !isDisabled;

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <label className="block space-y-2">
        <span className="text-sm font-semibold text-gray-900">Query</span>
        <textarea
          value={query}
          onChange={(e) => onChange(e.target.value)}
          disabled={isDisabled || isLoading}
          rows={4}
          placeholder="Enter your query..."
          className="w-full rounded-xl border border-gray-300 px-3 py-3 text-sm focus:border-blue-500 focus:outline-none disabled:bg-gray-50"
        />
      </label>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Button onClick={onRun} disabled={!canRun}>
          Run Comparison
        </Button>

        {isLoading ? (
          <div className="flex items-center gap-3 text-sm text-gray-500">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-200 border-t-blue-600" />
            <span>Running comparison across {stagedCount} configs...</span>
          </div>
        ) : (
          <p className="text-sm text-gray-400">
            {isActivated
              ? "Enter a query and run comparison."
              : "Add configs to staging and click Run & Save Configs to activate this query box."}
          </p>
        )}
      </div>
    </section>
  );
}
