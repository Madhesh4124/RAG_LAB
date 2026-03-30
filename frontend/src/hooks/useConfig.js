import { useState, useCallback } from "react";

const DEFAULTS = {
  chunker:     { type: "fixed_size", chunk_size: 512, overlap: 50, max_chunk_size: 512, pattern: "\\n\\n+", min_chunk_size: 100, window_size: 3 },
  embedder:    { provider: "google", model: "models/gemini-embedding-2-preview" },
  vectorstore: { type: "chroma", collection_name: "my_collection" },
  retriever:   { type: "hybrid", alpha: 0.7 },
  llm:         { provider: "gemini", model: "gemini-2.5-flash" },
};

const PRESETS = {
  fast:     { ...DEFAULTS, chunker: { type: "fixed_size", chunk_size: 256, overlap: 20 }, retriever: { type: "hybrid", top_k: 3, similarity_threshold: 0.6 } },
  balanced: { ...DEFAULTS },
  accurate: { ...DEFAULTS, chunker: { type: "semantic", max_chunk_size: 1024 }, embedder: { provider: "google", model: "models/gemini-embedding-2-preview" }, retriever: { type: "hybrid", top_k: 7, similarity_threshold: 0.8 } },
  recursive: { ...DEFAULTS, chunker: { type: "recursive", chunk_size: 512, overlap: 50, separators: ["\n\n", "\n", ". ", " "] } },
};

export function useConfig() {
  const [config, setConfig] = useState(DEFAULTS);
  const [step,   setStep]   = useState(0);
  const TOTAL_STEPS = 4; // upload, embedding, chunking, retrieval

  const updateSection = (section) => (val) =>
    setConfig((c) => ({ ...c, [section]: { ...c[section], ...val } }));

  return {
    config,
    step,
    TOTAL_STEPS,
    updateChunking:    updateSection("chunker"),
updateEmbedding:   updateSection("embedder"),
updateRetrieval:   updateSection("retriever"),
    applyPreset: (name) => setConfig(PRESETS[name] ?? DEFAULTS),
    nextStep: () => setStep((s) => Math.min(s + 1, TOTAL_STEPS)),
    prevStep: () => setStep((s) => Math.max(s - 1, 0)),
  };
}
