export default function DatasetBanner({ activeDataset, isDisabled }) {
  if (activeDataset) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
        <span className="text-xs uppercase tracking-wide text-gray-400">Active Dataset</span>
        <div className="mt-2 inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-sm text-gray-700">
          Using Dataset: <span className="ml-1 font-semibold text-gray-900">{activeDataset}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 ${isDisabled ? "opacity-100" : ""}`}>
      No dataset loaded. Please upload a document before using Compare.
    </div>
  );
}
