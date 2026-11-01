import React from 'react';
import { useMemo, useState } from "react";
import { Badge, Button } from "../common/index";

const EMBEDDING_MODELS = {
  nvidia: [
    { value: "nvidia/nemotron-3-embed-1b", label: "nvidia/nemotron-3-embed-1b (Default - 1024-dim)" },
  ],
  google: [
    { value: "models/gemini-embedding-001", label: "gemini-embedding-001 (Google API - 3072-dim)" },
    { value: "models/gemini-embedding-2-preview", label: "gemini-embedding-2-preview (Google API - 3072-dim)" },
  ],
  huggingface: [
    {
      value: "sentence-transformers/all-MiniLM-L6-v2",
      label: "sentence-transformers/all-MiniLM-L6-v2 (Local - 384-dim)",
    },
  ],
};

const CHUNK_STRATEGIES = [
  { value: "fixed_size", label: "Fixed Size" },
  { value: "recursive", label: "Recursive" },
  { value: "semantic", label: "Semantic" },
  { value: "chapter_based", label: "Chapter-Based" },
  { value: "regex", label: "Regex" },
  { value: "sentence_window", label: "Sentence Window" },
];

const DEFAULT_CHUNK_PARAMS = {
  fixed_size: { chunk_size: 512, overlap: 50 },
  recursive: {
    chunk_size: 512,
    overlap: 50,
    min_chunk_size: 100,
    separators: ["\n\n", "\n", "(?<=[.!?])\\s+", " "],
    apply_overlap_recursively: true,
  },
  semantic: {
    max_chunk_size: 512,
    min_chunk_size: 100,
    similarity_threshold: 0.7,
    hard_split_threshold: 0.4,
    overlap_sentences: 1,
  },
  chapter_based: { max_chunk_size: 1024, overlap_lines: 1 },
  regex: { pattern: "\\n\\n+", min_chunk_size: 100 },
  sentence_window: { window_size: 3, max_chunk_size: 150 },
};

export default function ConfigFormModal({ onSave, onCancel, existingNames = [], isDisabled }) {
  const [name, setName] = useState("");
  const [chunkStrategy, setChunkStrategy] = useState("fixed_size");
  const [chunkParams, setChunkParams] = useState({ ...DEFAULT_CHUNK_PARAMS.fixed_size });
  const [embeddingProvider, setEmbeddingProvider] = useState("nvidia");
  const [embeddingModel, setEmbeddingModel] = useState(EMBEDDING_MODELS.nvidia[0].value);
  const [retrievalType, setRetrievalType] = useState("hybrid");
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.5);
  const [alpha, setAlpha] = useState(0.7);
  const [lambdaMult, setLambdaMult] = useState(0.5);
  const [rerankerEnabled, setRerankerEnabled] = useState(false);
  const [rerankerModel, setRerankerModel] = useState("BAAI/bge-reranker-v2-m3");
  const [error, setError] = useState("");

  const normalizedName = useMemo(() => name.trim(), [name]);

  const availableEmbeddingModels = EMBEDDING_MODELS[embeddingProvider] || EMBEDDING_MODELS.nvidia;
  const activeEmbeddingModel = availableEmbeddingModels.some((m) => m.value === embeddingModel)
    ? embeddingModel
    : availableEmbeddingModels[0].value;

  const handleSubmit = () => {
    const trimmed = normalizedName;
    if (!trimmed) {
      setError("Config name is required.");
      return;
    }
    if (existingNames.some((item) => item.toLowerCase() === trimmed.toLowerCase())) {
      setError("A config with this name already exists.");
      return;
    }

    onSave({
      name: trimmed,
      chunk_strategy: chunkStrategy,
      chunk_params: chunkParams,
      embedding_provider: embeddingProvider,
      embedding_model: activeEmbeddingModel,
      retrieval_type: retrievalType,
      top_k: Number(topK),
      threshold: Number(threshold),
      similarity_threshold: Number(threshold),
      alpha: Number(alpha),
      lambda_mult: Number(lambdaMult),
      reranker_enabled: Boolean(rerankerEnabled),
      reranker_model: rerankerEnabled ? rerankerModel : undefined,
      reranker_provider: rerankerEnabled ? "huggingface_api" : undefined,
      isPreset: false,
      indexingStatus: "idle",
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className="w-full max-w-xl rounded-2xl border border-white/10 bg-surface-1 p-6 shadow-2xl space-y-5">
        <div className="flex items-start justify-between gap-3 border-b border-white/[0.08] pb-4">
          <div>
            <h3 className="text-xl font-bold text-[#FCF8D8] tracking-tight">Create Config</h3>
            <p className="text-xs text-[#D9DADF]/70 mt-0.5">Configure chunking, embeddings, and retrieval values.</p>
          </div>
          <Badge color="violet">Advanced</Badge>
        </div>

        {error && (
          <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-3.5 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          <label className="block space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Config Name</span>
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setError("");
              }}
              disabled={isDisabled}
              className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm text-white placeholder-white/30 focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
              placeholder="e.g. High Precision"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Chunking Strategy</span>
            <select
              value={chunkStrategy}
              onChange={(e) => {
                const nextStrategy = e.target.value;
                setChunkStrategy(nextStrategy);
                setChunkParams({ ...(DEFAULT_CHUNK_PARAMS[nextStrategy] || {}) });
              }}
              disabled={isDisabled}
              className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
            >
              {CHUNK_STRATEGIES.map((strategy) => (
                <option key={strategy.value} value={strategy.value} className="bg-surface-2 text-white">{strategy.label}</option>
              ))}
            </select>
          </label>

          {(chunkStrategy === "fixed_size" || chunkStrategy === "recursive") && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <NumericParam
                label="Chunk Size"
                value={chunkParams.chunk_size ?? 512}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, chunk_size: value }))}
                min={128}
                max={2048}
              />
              <NumericParam
                label="Overlap"
                value={chunkParams.overlap ?? 50}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, overlap: value }))}
                min={0}
                max={200}
              />
            </div>
          )}

          {chunkStrategy === "recursive" && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <NumericParam
                label="Min Chunk Size"
                value={chunkParams.min_chunk_size ?? 100}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, min_chunk_size: value }))}
                min={10}
                max={512}
              />
              <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-xs text-[#D9DADF]">
                <input
                  type="checkbox"
                  checked={chunkParams.apply_overlap_recursively ?? true}
                  onChange={(e) =>
                    setChunkParams((prev) => ({ ...prev, apply_overlap_recursively: e.target.checked }))
                  }
                  className="h-4 w-4 rounded border-white/20 accent-accent-violet"
                />
                Apply overlap recursively
              </label>
              <label className="block space-y-1.5 sm:col-span-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Separators (comma-separated)</span>
                <input
                  type="text"
                  value={Array.isArray(chunkParams.separators) ? chunkParams.separators.join(",") : ""}
                  onChange={(e) => {
                    const separators = e.target.value
                      .split(",")
                      .map((part) => part.trim())
                      .filter(Boolean);
                    setChunkParams((prev) => ({ ...prev, separators }));
                  }}
                  className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm font-mono text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
                />
              </label>
            </div>
          )}

          {chunkStrategy === "semantic" && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <NumericParam
                label="Max Chunk Size"
                value={chunkParams.max_chunk_size ?? 512}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, max_chunk_size: value }))}
                min={128}
                max={4096}
              />
              <NumericParam
                label="Min Chunk Size"
                value={chunkParams.min_chunk_size ?? 100}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, min_chunk_size: value }))}
                min={10}
                max={512}
              />
              <FloatParam
                label="Similarity Threshold"
                value={chunkParams.similarity_threshold ?? 0.7}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, similarity_threshold: value }))}
                min={0}
                max={1}
                step={0.01}
              />
              <FloatParam
                label="Hard Split Threshold"
                value={chunkParams.hard_split_threshold ?? 0.4}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, hard_split_threshold: value }))}
                min={0}
                max={1}
                step={0.01}
              />
              <NumericParam
                label="Overlap Sentences"
                value={chunkParams.overlap_sentences ?? 1}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, overlap_sentences: value }))}
                min={0}
                max={5}
              />
            </div>
          )}

          {chunkStrategy === "chapter_based" && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <NumericParam
                label="Max Chunk Size"
                value={chunkParams.max_chunk_size ?? 1024}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, max_chunk_size: value }))}
                min={256}
                max={4096}
              />
              <NumericParam
                label="Overlap Lines"
                value={chunkParams.overlap_lines ?? 1}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, overlap_lines: value }))}
                min={0}
                max={10}
              />
            </div>
          )}

          {chunkStrategy === "regex" && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="block space-y-1.5 sm:col-span-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Pattern</span>
                <input
                  type="text"
                  value={chunkParams.pattern ?? "\\n\\n+"}
                  onChange={(e) => setChunkParams((prev) => ({ ...prev, pattern: e.target.value }))}
                  className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm font-mono text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
                />
              </label>
              <NumericParam
                label="Min Chunk Size"
                value={chunkParams.min_chunk_size ?? 100}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, min_chunk_size: value }))}
                min={1}
                max={1024}
              />
            </div>
          )}

          {chunkStrategy === "sentence_window" && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <NumericParam
                label="Window Size"
                value={chunkParams.window_size ?? 3}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, window_size: value }))}
                min={1}
                max={7}
              />
              <NumericParam
                label="Max Chunk Size"
                value={chunkParams.max_chunk_size ?? 150}
                onChange={(value) => setChunkParams((prev) => ({ ...prev, max_chunk_size: value }))}
                min={50}
                max={150}
              />
            </div>
          )}

          <label className="block space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Embedding Provider</span>
            <select
              value={embeddingProvider}
              onChange={(e) => {
                const provider = e.target.value;
                setEmbeddingProvider(provider);
                setEmbeddingModel(EMBEDDING_MODELS[provider]?.[0]?.value || "");
              }}
              disabled={isDisabled}
              className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
            >
              <option value="nvidia" className="bg-surface-2 text-white">NVIDIA NIM</option>
              <option value="google" className="bg-surface-2 text-white">Google Gemini</option>
              <option value="huggingface" className="bg-surface-2 text-white">Hugging Face (Local)</option>
            </select>
          </label>

          <label className="block space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Embedding Model</span>
            <select
              value={activeEmbeddingModel}
              onChange={(e) => setEmbeddingModel(e.target.value)}
              disabled={isDisabled}
              className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
            >
              {availableEmbeddingModels.map((model) => (
                <option key={model.value} value={model.value} className="bg-surface-2 text-white">{model.label}</option>
              ))}
            </select>
          </label>

          {/* Retrieval Parameters Section */}
          <div className="pt-3 border-t border-white/[0.08] space-y-4">
            <div>
              <h4 className="text-sm font-bold text-[#FCF8D8] tracking-tight">Retrieval Parameters</h4>
              <p className="text-[11px] text-[#D9DADF]/60 mt-0.5">
                Configure search strategy, result limits, similarity filters, and optional rerankers.
              </p>
            </div>

            <label className="block space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">Retrieval Type</span>
              <select
                value={retrievalType}
                onChange={(e) => setRetrievalType(e.target.value)}
                disabled={isDisabled}
                className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2.5 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
              >
                <option value="dense" className="bg-surface-2 text-white">Dense (vector similarity)</option>
                <option value="sparse" className="bg-surface-2 text-white">Sparse (BM25 keyword)</option>
                <option value="hybrid" className="bg-surface-2 text-white">Hybrid (dense + sparse fusion)</option>
                <option value="mmr" className="bg-surface-2 text-white">MMR (Max Marginal Relevance)</option>
              </select>
            </label>

            <div className="grid gap-3 sm:grid-cols-2">
              {/* Top-K */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
                <div className="flex justify-between items-center text-sm">
                  <span className="font-semibold text-white/90">Top-K chunks</span>
                  <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{topK}</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  step={1}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  disabled={isDisabled}
                  className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
                />
                <p className="text-[11px] text-white/45">How many chunks to return</p>
              </div>

              {/* Similarity threshold */}
              {retrievalType !== "sparse" && (
                <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-semibold text-white/90">Similarity Threshold</span>
                    <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{Number(threshold).toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min={0.0}
                    max={1.0}
                    step={0.05}
                    value={threshold}
                    onChange={(e) => setThreshold(Number(e.target.value))}
                    disabled={isDisabled}
                    className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
                  />
                  <p className="text-[11px] text-white/45">Chunks below this score are discarded</p>
                </div>
              )}

              {/* Alpha for Hybrid */}
              {retrievalType === "hybrid" && (
                <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-semibold text-white/90">Alpha (Fusion Weight)</span>
                    <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{Number(alpha).toFixed(1)}</span>
                  </div>
                  <input
                    type="range"
                    min={0.0}
                    max={1.0}
                    step={0.1}
                    value={alpha}
                    onChange={(e) => setAlpha(Number(e.target.value))}
                    disabled={isDisabled}
                    className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
                  />
                  <p className="text-[11px] text-white/45">
                    Dense weight = {Number(alpha).toFixed(1)}, Sparse weight = {(1 - alpha).toFixed(1)}
                  </p>
                </div>
              )}

              {/* Lambda for MMR */}
              {retrievalType === "mmr" && (
                <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-semibold text-white/90">Lambda (MMR Trade-off)</span>
                    <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{Number(lambdaMult).toFixed(1)}</span>
                  </div>
                  <input
                    type="range"
                    min={0.0}
                    max={1.0}
                    step={0.1}
                    value={lambdaMult}
                    onChange={(e) => setLambdaMult(Number(e.target.value))}
                    disabled={isDisabled}
                    className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
                  />
                  <div className="flex justify-between text-[11px] text-white/45">
                    <span>Max Diversity</span>
                    <span>Max Relevance</span>
                  </div>
                </div>
              )}
            </div>

            {/* Reranker section */}
            <div className="space-y-3 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
              <label className="flex items-center justify-between cursor-pointer">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7] block">
                    Enable API Reranker
                  </span>
                  <span className="text-[11px] text-zinc-400">Re-scores candidates using cross-attention</span>
                </div>
                <input
                  type="checkbox"
                  checked={rerankerEnabled}
                  onChange={(e) => setRerankerEnabled(e.target.checked)}
                  disabled={isDisabled}
                  className="h-4 w-4 rounded border-white/20 accent-accent-violet cursor-pointer"
                />
              </label>
              {rerankerEnabled && (
                <div className="space-y-1.5 pt-2.5 border-t border-white/[0.08]">
                  <span className="text-[11px] font-medium text-white/70 block">Reranker Model (Hosted)</span>
                  <select
                    value={rerankerModel}
                    onChange={(e) => setRerankerModel(e.target.value)}
                    disabled={isDisabled}
                    className="w-full rounded-xl border border-white/10 bg-surface-2 px-3 py-2 text-xs text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
                  >
                    <option value="BAAI/bge-reranker-v2-m3" className="bg-surface-2 text-white">
                      BAAI/bge-reranker-v2-m3 (Best quality)
                    </option>
                    <option value="BAAI/bge-reranker-base" className="bg-surface-2 text-white">
                      BAAI/bge-reranker-base (Accurate)
                    </option>
                  </select>
                </div>
              )}
            </div>

            {/* Summary box */}
            <div className="rounded-xl bg-surface-2/70 border border-white/10 p-3.5 text-xs text-white/80 space-y-1">
              <p className="font-semibold text-white flex items-center gap-1.5">
                <span>📋</span> Config Summary
              </p>
              <p className="text-white/70">
                Using <strong className="text-white capitalize">{retrievalType}</strong> retrieval. Selecting up to <strong className="text-accent-violet-light">{topK} chunks</strong>
                {retrievalType === "hybrid" ? ` (α = ${Number(alpha).toFixed(1)})` : ""}
                {retrievalType === "mmr" ? ` (λ = ${Number(lambdaMult).toFixed(1)})` : ""}
                {rerankerEnabled ? ` with ${rerankerModel.split("/").pop()} reranker` : ""}.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-white/[0.08] flex justify-end gap-2.5">
          <Button variant="secondary" onClick={onCancel} disabled={isDisabled}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isDisabled}>Save Config</Button>
        </div>
      </div>
    </div>
  );
}

function NumericParam({ label, value, onChange, min, max }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
        className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
      />
    </label>
  );
}

function FloatParam({ label, value, onChange, min, max, step }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
        className="w-full rounded-xl border border-white/10 bg-surface-2 px-3.5 py-2 text-sm text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
      />
    </label>
  );
}
