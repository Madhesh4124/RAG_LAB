import React from 'react';
import { useMemo, useState } from "react";
import { Badge, Button } from "../common/index";

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
  const [error, setError] = useState("");

  const normalizedName = useMemo(() => name.trim(), [name]);

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
      embedding_model: embeddingModel,
      top_k: Number(topK),
      threshold: Number(threshold),
      isPreset: false,
      indexingStatus: "indexing",
    });
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg rounded-2xl border border-gray-200 bg-white p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Create Config</h3>
            <p className="text-sm text-gray-500">Configure chunking, embeddings, and retrieval values.</p>
          </div>
          <Badge color="blue">Advanced</Badge>
        </div>

        <div className="mt-5 space-y-4">
          <label className="block space-y-1">
            <span className="text-sm font-medium text-gray-700">Config Name</span>
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setError("");
              }}
              disabled={isDisabled}
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="e.g. High Precision"
            />
          </label>

          <label className="block space-y-1">
            <span className="text-sm font-medium text-gray-700">Chunking Strategy</span>
            <select
              value={chunkStrategy}
              onChange={(e) => {
                const nextStrategy = e.target.value;
                setChunkStrategy(nextStrategy);
                setChunkParams({ ...(DEFAULT_CHUNK_PARAMS[nextStrategy] || {}) });
              }}
              disabled={isDisabled}
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {CHUNK_STRATEGIES.map((strategy) => (
                <option key={strategy.value} value={strategy.value}>{strategy.label}</option>
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
              <label className="flex items-center gap-2 rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={chunkParams.apply_overlap_recursively ?? true}
                  onChange={(e) =>
                    setChunkParams((prev) => ({ ...prev, apply_overlap_recursively: e.target.checked }))
                  }
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                Apply overlap recursively
              </label>
              <label className="block space-y-1 sm:col-span-2">
                <span className="text-sm font-medium text-gray-700">Separators (comma-separated)</span>
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
                  className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none"
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
              <label className="block space-y-1 sm:col-span-2">
                <span className="text-sm font-medium text-gray-700">Pattern</span>
                <input
                  type="text"
                  value={chunkParams.pattern ?? "\\n\\n+"}
                  onChange={(e) => setChunkParams((prev) => ({ ...prev, pattern: e.target.value }))}
                  className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none"
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

          <label className="block space-y-1">
            <span className="text-sm font-medium text-gray-700">Embedding Provider</span>
            <select
              value={embeddingProvider}
              onChange={(e) => {
                const provider = e.target.value;
                setEmbeddingProvider(provider);
                setEmbeddingModel(EMBEDDING_MODELS[provider][0].value);
              }}
              disabled={isDisabled}
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="nvidia">NVIDIA</option>
              <option value="huggingface">Hugging Face</option>
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-sm font-medium text-gray-700">Embedding Model</span>
            <select
              value={embeddingModel}
              onChange={(e) => setEmbeddingModel(e.target.value)}
              disabled={isDisabled}
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {EMBEDDING_MODELS[embeddingProvider].map((model) => (
                <option key={model.value} value={model.value}>{model.label}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-2">
            <div className="flex items-center justify-between text-sm font-medium text-gray-700">
              <span>top_k</span>
              <span className="font-mono text-blue-600">{topK}</span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              step={1}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              disabled={isDisabled}
              className="w-full accent-blue-600"
            />
          </label>

          <label className="block space-y-2">
            <div className="flex items-center justify-between text-sm font-medium text-gray-700">
              <span>Similarity Threshold</span>
              <span className="font-mono text-blue-600">{Number(threshold).toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              disabled={isDisabled}
              className="w-full accent-blue-600"
            />
          </label>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={isDisabled}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isDisabled}>Save Config</Button>
        </div>
      </div>
    </div>
  );
}

function NumericParam({ label, value, onChange, min, max }) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
        className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />
    </label>
  );
}

function FloatParam({ label, value, onChange, min, max, step }) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
        className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      />
    </label>
  );
}
