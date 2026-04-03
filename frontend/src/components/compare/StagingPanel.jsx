import { Button } from "../common/index";

export default function StagingPanel({
  stagedConfigs,
  onRemove,
  onClearAll,
  onRunStaged,
  isDisabled,
  isRunningStaged,
  isRunEnabled,
}) {
  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Staging Panel</h2>
          <p className="text-sm text-gray-500">Prepare up to four configs for a side-by-side comparison.</p>
        </div>
        <div className="text-sm text-gray-500">{stagedConfigs.length} / 4 configs staged</div>
      </div>

      <div className="mt-4 space-y-2">
        {stagedConfigs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-sm text-gray-400">
            No configs staged yet.
          </div>
        ) : (
          stagedConfigs.map((config) => (
            <div key={config.name} className="flex items-center justify-between rounded-xl border border-gray-200 px-4 py-3">
              <div>
                <p className="font-medium text-gray-900">{config.name}</p>
                <p className="text-sm text-gray-500">top_k: {config.top_k} · threshold: {Number(config.threshold).toFixed(2)}</p>
              </div>
              <button
                type="button"
                onClick={() => onRemove(config.name)}
                disabled={isDisabled}
                className="rounded-full px-2 py-1 text-sm text-gray-500 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
                aria-label={`Remove ${config.name}`}
              >
                ❌
              </button>
            </div>
          ))
        )}
      </div>

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <Button onClick={onRunStaged} disabled={!isRunEnabled}>
          {isRunningStaged ? "Running & Saving..." : "Run & Save Configs"}
        </Button>
        <Button variant="secondary" onClick={onClearAll} disabled={isDisabled || stagedConfigs.length === 0}>
          Clear All
        </Button>
      </div>
    </section>
  );
}
