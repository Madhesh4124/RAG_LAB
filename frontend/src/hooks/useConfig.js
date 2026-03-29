import { useState, useCallback } from "react";

const DEFAULTS = {
  chunker:     { type: "fixed_size", chunk_size: 512, overlap: 50 },
  embedder:    { provider: "google", model: "models/gemini-embedding-2-preview" },
  vectorstore: { type: "chroma", collection_name: "my_collection" },
  retriever:   { type: "hybrid", alpha: 0.7 },
  llm:         { provider: "gemini", model: "gemini-2.5-flash" },
};

const PRESETS = {
  fast:     { ...DEFAULTS, chunker: { type: "fixed_size", chunk_size: 256, overlap: 20 }, retriever: { type: "hybrid", top_k: 3, similarity_threshold: 0.6 } },
  balanced: { ...DEFAULTS },
  accurate: { ...DEFAULTS, chunker: { type: "semantic", chunk_size: 1024, overlap: 100 }, embedder: { provider: "google", model: "models/gemini-embedding-2-preview" }, retriever: { type: "hybrid", top_k: 7, similarity_threshold: 0.8 } },
};

export function useConfig() {
  const [config, setConfig] = useState(DEFAULTS);
  const [step,   setStep]   = useState(0);
  const TOTAL_STEPS = 5; // upload, chunking, embedding, vectorstore, retrieval

  const updateSection = (section) => (val) =>
    setConfig((c) => ({ ...c, [section]: { ...c[section], ...val } }));

  return {
    config,
    step,
    TOTAL_STEPS,
    updateChunking:    updateSection("chunker"),
updateEmbedding:   updateSection("embedder"),
updateVectorstore: updateSection("vectorstore"),
updateRetrieval:   updateSection("retriever"),
    applyPreset: (name) => setConfig(PRESETS[name] ?? DEFAULTS),
    nextStep: () => setStep((s) => Math.min(s + 1, TOTAL_STEPS)),
    prevStep: () => setStep((s) => Math.max(s - 1, 0)),
  };
}
