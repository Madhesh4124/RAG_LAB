import { useState, useCallback } from "react";

const DEFAULTS = {
  chunking:    { strategy: "fixed_size", chunk_size: 512, overlap: 50 },
  embedding:   { model: "nomic" },
  vectorstore: { type: "chroma" },
  retrieval:   { top_k: 5, similarity_threshold: 0.7 },
};

const PRESETS = {
  fast:     { ...DEFAULTS, chunking: { strategy: "fixed_size", chunk_size: 256, overlap: 20 }, retrieval: { top_k: 3, similarity_threshold: 0.6 } },
  balanced: { ...DEFAULTS },
  accurate: { ...DEFAULTS, chunking: { strategy: "semantic", chunk_size: 1024, overlap: 100 }, embedding: { model: "openai" }, retrieval: { top_k: 7, similarity_threshold: 0.8 } },
};

export function useConfig() {
  const [config, setConfig] = useState(DEFAULTS);
  const [step,   setStep]   = useState(0);
  const TOTAL_STEPS = 4; // chunking, embedding, vectorstore, retrieval

  const updateSection = (section) => (val) =>
    setConfig((c) => ({ ...c, [section]: { ...c[section], ...val } }));

  return {
    config,
    step,
    TOTAL_STEPS,
    updateChunking:     updateSection("chunking"),
    updateEmbedding:    updateSection("embedding"),
    updateVectorstore:  updateSection("vectorstore"),
    updateRetrieval:    updateSection("retrieval"),
    applyPreset: (name) => setConfig(PRESETS[name] ?? DEFAULTS),
    nextStep: () => setStep((s) => Math.min(s + 1, TOTAL_STEPS)),
    prevStep: () => setStep((s) => Math.max(s - 1, 0)),
  };
}
