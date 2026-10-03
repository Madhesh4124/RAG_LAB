// ── EmbeddingStep ────────────────────────────────────────────────
const EMBEDDING_MODELS = {
  nvidia: [
    { value: "nvidia/nemotron-3-embed-1b", label: "nvidia/nemotron-3-embed-1b (Default - 1024-dim)" },
  ],
  huggingface: [
    { value: "BAAI/bge-base-en-v1.5", label: "BAAI/bge-base-en-v1.5 (High Quality - 768-dim)" },
    {
      value: "sentence-transformers/all-MiniLM-L6-v2",
      label: "sentence-transformers/all-MiniLM-L6-v2 (Fast - 384-dim)",
    },
    {
      value: "sentence-transformers/multi-qa-mpnet-base-dot-v1",
      label: "sentence-transformers/multi-qa-mpnet-base-dot-v1 (QA Optimized)",
    },
  ],
};

export function EmbeddingStep({ config, onChange }) {
  const selectedProvider = config.provider === "huggingface" ? "huggingface" : "nvidia";
  const providerModels = EMBEDDING_MODELS[selectedProvider];
  const selectedModel =
    providerModels.find((m) => m.value === config.model)?.value || providerModels[0].value;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">Embedding Model</h2>
        <p className="text-sm text-white/60 mt-0.5">Select the vector representation model for indexing and semantic similarity matching.</p>
      </div>

      <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-6 space-y-5">
        <div className="space-y-2">
          <label className="text-xs font-semibold text-white/70 uppercase tracking-wider" htmlFor="embed-provider">
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
            className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
          >
            <option value="nvidia" className="bg-surface-2 text-white">NVIDIA NIM</option>
            <option value="huggingface" className="bg-surface-2 text-white">Hugging Face</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-semibold text-white/70 uppercase tracking-wider" htmlFor="embed-model">
            Model
          </label>
          <select
            id="embed-model"
            value={selectedModel}
            onChange={(e) => onChange({ provider: selectedProvider, model: e.target.value })}
            className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
          >
            {providerModels.map((model) => (
              <option key={model.value} value={model.value} className="bg-surface-2 text-white">
                {model.label}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-xl bg-surface-2/60 border border-white/[0.07] p-4 text-xs text-white/70 flex items-center justify-between">
          <span>Active Provider: <strong className="text-white capitalize">{selectedProvider}</strong></span>
          <span className="font-mono text-accent-violet-light bg-accent-violet/15 px-2.5 py-0.5 rounded border border-accent-violet/30">{selectedModel}</span>
        </div>
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
    <div className="space-y-6">
      <div>
        <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">Retrieval Parameters</h2>
        <p className="text-sm text-white/60 mt-0.5">Configure search strategy, result limits, similarity filters, and optional rerankers.</p>
      </div>

      <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-6 space-y-5">
        <div className="space-y-2">
          <label className="text-xs font-semibold text-white/70 uppercase tracking-wider">Retrieval Type</label>
          <select
            value={retrievalType}
            onChange={(e) => onChange({ retrieval_type: e.target.value, type: e.target.value })}
            className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
          >
            <option value="dense" className="bg-surface-2 text-white">Dense (vector similarity)</option>
            <option value="sparse" className="bg-surface-2 text-white">Sparse (BM25 keyword)</option>
            <option value="hybrid" className="bg-surface-2 text-white">Hybrid (dense + sparse fusion)</option>
            <option value="mmr" className="bg-surface-2 text-white">MMR (Max Marginal Relevance)</option>
          </select>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {/* Top-K */}
          <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
            <div className="flex justify-between items-center text-sm">
              <span className="font-semibold text-white/90">Top-K chunks</span>
              <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{topK}</span>
            </div>
            <input
              type="range" min={1} max={10} step={1} value={topK}
              onChange={(e) => onChange({ top_k: Number(e.target.value) })}
              className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
            />
            <p className="text-[11px] text-white/45">How many chunks to return</p>
          </div>

          {/* Similarity threshold */}
          {retrievalType !== "sparse" && (
            <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
              <div className="flex justify-between items-center text-sm">
                <span className="font-semibold text-white/90">Similarity Threshold</span>
                <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{similarityThreshold}</span>
              </div>
              <input
                type="range" min={0.1} max={1.0} step={0.05} value={similarityThreshold}
                onChange={(e) => onChange({ similarity_threshold: Number(e.target.value) })}
                className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
              />
              <p className="text-[11px] text-white/45">Chunks below this score are discarded</p>
            </div>
          )}

          {/* Alpha */}
          {retrievalType === "hybrid" && (
            <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
              <div className="flex justify-between items-center text-sm">
                <span className="font-semibold text-white/90">Alpha (Fusion Weight)</span>
                <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{alpha}</span>
              </div>
              <input
                type="range" min={0.0} max={1.0} step={0.1} value={alpha}
                onChange={(e) => onChange({ alpha: Number(e.target.value) })}
                className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
              />
              <p className="text-[11px] text-white/45">
                Dense weight = {alpha}, Sparse weight = {(1 - alpha).toFixed(1)}
              </p>
            </div>
          )}

          {/* Lambda for MMR */}
          {retrievalType === "mmr" && (
            <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
              <div className="flex justify-between items-center text-sm">
                <span className="font-semibold text-white/90">Lambda (MMR Trade-off)</span>
                <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{lambdaMult}</span>
              </div>
              <input
                type="range" min={0.0} max={1.0} step={0.1} value={lambdaMult}
                onChange={(e) => onChange({ lambda_mult: Number(e.target.value) })}
                className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
              />
              <div className="flex justify-between text-[11px] text-white/45">
                <span>Max Diversity</span>
                <span>Max Relevance</span>
              </div>
            </div>
          )}
        </div>

        {/* Reranker */}
        <div className="space-y-3 pt-4 border-t border-white/[0.08]">
          <label className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={config.reranker_enabled || false}
              onChange={(e) => onChange({ reranker_enabled: e.target.checked })}
              className="h-4 w-4 rounded border-white/20 bg-surface-1 text-accent-violet accent-accent-violet focus:ring-accent-violet cursor-pointer"
            />
            <span className="text-sm font-semibold text-white">Enable API Reranker</span>
          </label>
          {config.reranker_enabled && (
            <div className="space-y-2 pl-6">
              <label className="text-xs font-semibold text-white/70">Reranker Model (Hosted)</label>
              <select
                value={config.reranker_model || "BAAI/bge-reranker-base"}
                onChange={(e) => onChange({ reranker_provider: "huggingface_api", reranker_model: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-surface-2 px-3 py-2 text-sm text-white focus:border-accent-violet outline-none"
              >
                <option value="BAAI/bge-reranker-large" className="bg-surface-2 text-white">BAAI/bge-reranker-large (Best quality)</option>
                <option value="BAAI/bge-reranker-base" className="bg-surface-2 text-white">BAAI/bge-reranker-base (Accurate)</option>
              </select>
            </div>
          )}
        </div>

        {/* Summary box */}
        <div className="rounded-xl bg-surface-2/70 border border-white/10 p-4 text-xs text-white/80 space-y-1">
          <p className="font-semibold text-white flex items-center gap-1.5">
            <span>📋</span> Config Summary
          </p>
          <p className="text-white/70">Using <strong className="text-white capitalize">{retrievalType}</strong> retrieval. Selecting up to <strong className="text-accent-violet-light">{topK} chunks</strong>.</p>
        </div>
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
        <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">LLM & Memory</h2>
        <p className="text-sm text-white/60 mt-0.5">Configure generation model resiliency and conversational memory retention.</p>
      </div>

      {/* LLM Model */}
      <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-6 space-y-4">
        <div>
          <label className="text-xs font-semibold text-white/70 uppercase tracking-wider">Active LLM Architecture</label>
          <div className="mt-2.5 flex items-center justify-between p-3.5 rounded-xl border border-white/10 bg-surface-2/80">
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-sm font-bold text-white">gemini-2.5-flash</span>
              <span className="text-xs text-white/50">(Google AI Studio)</span>
            </div>
            <span className="text-[11px] font-semibold text-accent-violet-light bg-accent-violet/15 px-2.5 py-1 rounded-lg border border-accent-violet/25">
              Primary LLM
            </span>
          </div>
          <div className="mt-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs text-white/60 space-y-1">
            <p className="font-semibold text-white/80">Resilient Fallback Hierarchy:</p>
            <p className="text-[11px] font-mono text-white/50">
              1. Google Gemini 2.5 Flash ➔ 2. NVIDIA Nemotron 3.5 30B ➔ 3. Groq GPT-OSS 120B
            </p>
          </div>
        </div>
      </div>

      {/* Memory Configuration */}
      <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-6 space-y-5">
        <div className="space-y-2">
          <label className="text-xs font-semibold text-white/70 uppercase tracking-wider">Memory Strategy</label>
          <select
            value={memoryType}
            onChange={(e) => onMemoryChange({ type: e.target.value })}
            className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
          >
            <option value="none" className="bg-surface-2 text-white">None (No session recall)</option>
            <option value="buffer" className="bg-surface-2 text-white">Buffer (Fixed recent turns)</option>
            <option value="summary" className="bg-surface-2 text-white">Summary (Long-term compression)</option>
          </select>
        </div>

        {memoryType === "buffer" && (
          <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
            <div className="flex justify-between items-center text-sm">
              <span className="font-semibold text-white/90">Max Recall Turns</span>
              <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{maxTurns}</span>
            </div>
            <input 
              type="range" min={1} max={20} step={1} 
              value={maxTurns}
              onChange={(e) => onMemoryChange({ max_turns: Number(e.target.value) })}
              className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet" 
            />
            <p className="text-[11px] text-white/45">Retains exact verbatim user/assistant turns in memory.</p>
          </div>
        )}

        {memoryType === "summary" && (
          <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
            <div className="flex justify-between items-center text-sm">
              <span className="font-semibold text-white/90">Summary Frequency (turns)</span>
              <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{maxTurnsBeforeSummary}</span>
            </div>
            <input 
              type="range" min={2} max={10} step={1} 
              value={maxTurnsBeforeSummary}
              onChange={(e) => onMemoryChange({ max_turns_before_summary: Number(e.target.value) })}
              className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet" 
            />
            <p className="text-[11px] text-white/45">Frequency at which old dialogue is distilled into a concise summary.</p>
          </div>
        )}

        <div className="rounded-xl bg-accent-violet/[0.12] border border-accent-violet/25 p-4 flex items-start gap-3">
          <span className="text-accent-violet-light text-base">💡</span>
          <p className="text-xs text-white/80 leading-relaxed">
            {memoryType === "buffer" ? "Buffer memory keeps the exact text of the last few turns for immediate follow-up references." : 
             memoryType === "summary" ? "Summary memory compresses older turns into a concise context block, saving context tokens for long discussions." : 
             "No memory treats each query in isolation without retaining preceding conversation history."}
          </p>
        </div>
      </div>
    </div>
  );
}
