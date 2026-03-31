// ── EmbeddingStep ────────────────────────────────────────────────
const EMBEDDING_MODELS = {
  nvidia: [
    { value: "nvidia/nv-embed-v1", label: "nvidia/nv-embed-v1 (Default)" },
    {
      value: "nvidia/llama-3.2-nemoretriever-300m-embed-v1",
      label: "nvidia/llama-3.2-nemoretriever-300m-embed-v1",
    },
  ],
  huggingface: [
    {
      value: "sentence-transformers/all-MiniLM-L6-v2",
      label: "sentence-transformers/all-MiniLM-L6-v2",
    },
    { value: "BAAI/bge-base-en-v1.5", label: "BAAI/bge-base-en-v1.5" },
    { value: "intfloat/e5-base-v2", label: "intfloat/e5-base-v2" },
    { value: "thenlper/gte-base", label: "thenlper/gte-base" },
    {
      value: "sentence-transformers/multi-qa-mpnet-base-dot-v1",
      label: "sentence-transformers/multi-qa-mpnet-base-dot-v1",
    },
  ],
};

export function EmbeddingStep({ config, onChange }) {
  const selectedProvider = config.provider === "huggingface" ? "huggingface" : "nvidia";
  const providerModels = EMBEDDING_MODELS[selectedProvider];
  const selectedModel =
    providerModels.find((m) => m.value === config.model)?.value || providerModels[0].value;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Embedding Model</h2>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
        <label className="text-sm font-medium text-gray-700" htmlFor="embed-provider">
          Provider
        </label>
        <select
          id="embed-provider"
          value={selectedProvider}
          onChange={(e) => {
            const provider = e.target.value;
            const fallbackModel = EMBEDDING_MODELS[provider][0].value;
            onChange({ provider, model: fallbackModel });
          }}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="nvidia">NVIDIA</option>
          <option value="huggingface">Hugging Face</option>
        </select>

        <label className="text-sm font-medium text-gray-700" htmlFor="embed-model">
          Model
        </label>
        <select
          id="embed-model"
          value={selectedModel}
          onChange={(e) => onChange({ provider: selectedProvider, model: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          {providerModels.map((model) => (
            <option key={model.value} value={model.value}>
              {model.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

// ── RetrievalStep ────────────────────────────────────────────────
export function RetrievalStep({ config, onChange }) {
  const topK = config.top_k ?? 5;
  const similarityThreshold = config.similarity_threshold ?? 0.7;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Retrieval Parameters</h2>
        <p className="text-sm text-gray-500">How many chunks to fetch and how strict the similarity filter is.</p>
      </div>

      {/* Top-K */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700">Top-K chunks</span>
          <span className="text-blue-600 font-mono">{topK}</span>
        </div>
        <input type="range" min={1} max={10} step={1} value={topK}
          onChange={(e) => onChange({ top_k: Number(e.target.value) })}
          className="w-full accent-blue-600" />
        <p className="text-xs text-gray-400">How many chunks to pass to the LLM</p>
      </div>

      {/* Similarity threshold */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700">Similarity Threshold</span>
          <span className="text-blue-600 font-mono">{similarityThreshold}</span>
        </div>
        <input type="range" min={0.1} max={1.0} step={0.05} value={similarityThreshold}
          onChange={(e) => onChange({ similarity_threshold: Number(e.target.value) })}
          className="w-full accent-blue-600" />
        <p className="text-xs text-gray-400">Chunks below this score are discarded</p>
      </div>

      {/* Summary box */}
      <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 text-xs text-gray-600 space-y-1">
        <p className="font-semibold text-gray-700">📋 Config Summary</p>
        <p>Will retrieve up to <strong>{topK} chunks</strong> with similarity ≥ <strong>{similarityThreshold}</strong></p>
      </div>
    </div>
  );
}
