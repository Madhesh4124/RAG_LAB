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
  const retrievalType = config.retrieval_type || config.type || "hybrid";
  const topK = config.top_k ?? 5;
  const similarityThreshold = config.similarity_threshold ?? 0.7;
  const alpha = config.alpha ?? 0.7;
  const lambdaMult = config.lambda_mult ?? 0.5;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Retrieval Parameters</h2>
        <p className="text-sm text-gray-500">Select strategy and parameters.</p>
      </div>

      <div className="space-y-1">
        <label className="text-sm font-medium text-gray-700">Retrieval Type</label>
        <select
          value={retrievalType}
          onChange={(e) => onChange({ retrieval_type: e.target.value, type: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="dense">Dense (vector similarity)</option>
          <option value="sparse">Sparse (BM25 keyword)</option>
          <option value="hybrid">Hybrid (fusion)</option>
          <option value="mmr">MMR (Max Marginal Relevance)</option>
        </select>
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
        <p className="text-xs text-gray-400">How many chunks to return</p>
      </div>

      {/* Similarity threshold */}
      {retrievalType !== "sparse" && (
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
      )}

      {/* Alpha */}
      {retrievalType === "hybrid" && (
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700">Alpha (Fusion Weight)</span>
          <span className="text-blue-600 font-mono">{alpha}</span>
        </div>
        <input type="range" min={0.0} max={1.0} step={0.1} value={alpha}
          onChange={(e) => onChange({ alpha: Number(e.target.value) })}
          className="w-full accent-blue-600" />
        <p className="text-xs text-gray-400">
          Dense weight = {alpha}, Sparse weight = {(1 - alpha).toFixed(1)}
        </p>
      </div>
      )}

      {/* Lambda for MMR */}
      {retrievalType === "mmr" && (
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700">Lambda (MMR Trade-off)</span>
          <span className="text-blue-600 font-mono">{lambdaMult}</span>
        </div>
        <input type="range" min={0.0} max={1.0} step={0.1} value={lambdaMult}
          onChange={(e) => onChange({ lambda_mult: Number(e.target.value) })}
          className="w-full accent-blue-600" />
        <div className="flex justify-between text-xs text-gray-400">
          <span>Max Diversity</span>
          <span>Max Relevance</span>
        </div>
      </div>
      )}

      {/* Reranker */}
      <div className="space-y-3 pt-4 border-t border-gray-100">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input type="checkbox" checked={config.reranker_enabled || false}
             onChange={(e) => onChange({ reranker_enabled: e.target.checked })}
             className="accent-blue-600 rounded text-blue-600 w-4 h-4" />
         <span className="text-sm font-medium text-gray-700">Enable API Reranker</span>
        </label>
        {config.reranker_enabled && (
           <div className="space-y-1 pl-6">
           <label className="text-xs font-medium text-gray-600">Reranker Model (Hosted)</label>
             <select
             value={config.reranker_model || "BAAI/bge-reranker-base"}
             onChange={(e) => onChange({ reranker_provider: "huggingface_api", reranker_model: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
             >
             <option value="BAAI/bge-reranker-large">BAAI/bge-reranker-large (Best quality)</option>
                <option value="BAAI/bge-reranker-base">BAAI/bge-reranker-base (Accurate)</option>
             </select>
           </div>
        )}
      </div>

      {/* Summary box */}
      <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 text-xs text-gray-600 space-y-1">
        <p className="font-semibold text-gray-700">📋 Config Summary</p>
        <p>Using <strong>{retrievalType}</strong> retrieval. Will select up to <strong>{topK} chunks</strong>.</p>
      </div>
    </div>
  );
}

// ── LLMStep ──────────────────────────────────────────────────
export function LLMStep({ memoryConfig, onMemoryChange }) {
  const memoryType = memoryConfig.type || "buffer";
  const maxTurns = memoryConfig.max_turns ?? 5;
  const maxTurnsBeforeSummary = memoryConfig.max_turns_before_summary ?? 5;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">LLM & Memory</h2>
        <p className="text-sm text-gray-500">Configure response generation and conversation recall.</p>
      </div>

      {/* LLM Model */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
        <label className="text-sm font-medium text-gray-700">Model</label>
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800">
          Gemini 2.5 Flash
        </div>
        <p className="text-xs text-gray-400">Gemini is used for answer synthesis.</p>
      </div>

      {/* Memory Configuration */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-4">
        <label className="text-sm font-medium text-gray-700">Memory Type</label>
        <select
          value={memoryType}
          onChange={(e) => onMemoryChange({ type: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="none">None (No session recall)</option>
          <option value="buffer">Buffer (Fixed recent turns)</option>
          <option value="summary">Summary (Long-term compression)</option>
        </select>

        {memoryType === "buffer" && (
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Max Recall Turns</span>
              <span className="text-blue-600 font-mono">{maxTurns}</span>
            </div>
            <input 
              type="range" min={1} max={20} step={1} 
              value={maxTurns}
              onChange={(e) => onMemoryChange({ max_turns: Number(e.target.value) })}
              className="w-full accent-blue-600" 
            />
          </div>
        )}

        {memoryType === "summary" && (
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Summary Frequency (turns)</span>
              <span className="text-blue-600 font-mono">{maxTurnsBeforeSummary}</span>
            </div>
            <input 
              type="range" min={2} max={10} step={1} 
              value={maxTurnsBeforeSummary}
              onChange={(e) => onMemoryChange({ max_turns_before_summary: Number(e.target.value) })}
              className="w-full accent-blue-600" 
            />
          </div>
        )}
      </div>

      <div className="rounded-lg bg-blue-50 border border-blue-100 p-3 flex items-start space-x-2">
        <span className="text-blue-500 text-sm">💡</span>
        <p className="text-xs text-blue-700">
          {memoryType === "buffer" ? "Buffer memory keeps the exact text of the last few turns." : 
           memoryType === "summary" ? "Summary memory compresses old turns into a brief context." : 
           "No memory means every question is treated in isolation."}
        </p>
      </div>
    </div>
  );
}
