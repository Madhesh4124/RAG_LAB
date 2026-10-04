import React from 'react';
import { useMemo, useState } from "react";
import { Badge, Button } from "../common/index";

const EMBEDDING_MODELS = {
  nvidia: [
    { value: "nvidia/nemotron-3-embed-1b", label: "nvidia/nemotron-3-embed-1b (Default - 1024-dim)" },
  ],
  huggingface: [
    {
      value: "sentence-transformers/all-MiniLM-L6-v2",
      label: "sentence-transformers/all-MiniLM-L6-v2 (Default - 384-dim)",
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
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.5);
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
      top_k: Number(topK),
      threshold: Number(threshold),
      reranker_enabled: Boolean(rerankerEnabled),
      reranker_model: rerankerEnabled ? rerankerModel : undefined,
      isPreset: false,
      indexingStatus: "indexing",
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-surface-1 p-6 shadow-2xl space-y-5">
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

        <div className="space-y-4 max-h-[65vh] overflow-y-auto pr-1">
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
              <option value="nvidia" className="bg-surface-2 text-white">NVIDIA</option>
              <option value="huggingface" className="bg-surface-2 text-white">Hugging Face</option>
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

          <div className="space-y-2 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">
              <span>top_k</span>
              <span className="font-mono text-accent-violet-light font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{topK}</span>
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
          </div>

          <div className="space-y-2 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#ADACA7]">
              <span>Similarity Threshold</span>
              <span className="font-mono text-accent-violet-light font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">{Number(threshold).toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              disabled={isDisabled}
              className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
            />
          </div>

          {/* Reranker section */}
          <div className="space-y-3 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-[#ADACA7] block">
                  Enable Reranker
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
                <span className="text-[11px] font-medium text-white/70 block">Reranker Model</span>
                <select
                  value={rerankerModel}
                  onChange={(e) => setRerankerModel(e.target.value)}
                  disabled={isDisabled}
                  className="w-full rounded-xl border border-white/10 bg-surface-2 px-3 py-2 text-xs text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none transition-all"
                >
                  <option value="BAAI/bge-reranker-v2-m3" className="bg-surface-2 text-white">
                    BAAI/bge-reranker-v2-m3 (Hosted API - Best Quality)
                  </option>
                  <option value="BAAI/bge-reranker-base" className="bg-surface-2 text-white">
                    BAAI/bge-reranker-base (Hosted API - Fast)
                  </option>
                </select>
              </div>
            )}
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
