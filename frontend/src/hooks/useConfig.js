import { useState } from "react";

const RECURSIVE_SEPARATORS = ["\n\n", "\n", "(?<=[.!?])\\s+", " "];

const CHUNKER_DEFAULTS = {
  fixed_size: { type: "fixed_size", chunk_size: 512, overlap: 50 },
  recursive: {
    type: "recursive",
    chunk_size: 512,
    overlap: 50,
    min_chunk_size: 100,
    separators: RECURSIVE_SEPARATORS,
    apply_overlap_recursively: true,
  },
  semantic: {
    type: "semantic",
    max_chunk_size: 512,
    min_chunk_size: 100,
    similarity_threshold: 0.7,
    hard_split_threshold: 0.4,
    overlap_sentences: 1,
  },
  chapter_based: { type: "chapter_based", max_chunk_size: 1024, overlap_lines: 1 },
  sentence_window: { type: "sentence_window", window_size: 3, max_chunk_size: 150 },
  regex: { type: "regex", pattern: "\\n\\n+", min_chunk_size: 100 },
};

const DEFAULTS = {
  chunker:     CHUNKER_DEFAULTS.fixed_size,
  embedder:    { provider: "nvidia", model: "nvidia/nv-embed-v1" },
  vectorstore: { type: "chroma", collection_name: "my_collection" },
  retriever:   { type: "hybrid", retrieval_type: "hybrid", top_k: 5, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" },
  llm:         { provider: "gemini", model: "gemma-4-26b-a4b-it" },
  memory:      { type: "buffer", max_turns: 5, max_turns_before_summary: 5 },
};

const PRESETS = {
  fast:     { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.fixed_size, chunk_size: 256, overlap: 20 }, retriever: { type: "hybrid", retrieval_type: "hybrid", top_k: 3, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
  balanced: { ...DEFAULTS },
  accurate: { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.semantic, max_chunk_size: 1024, similarity_threshold: 0.7, overlap_sentences: 1 }, embedder: { provider: "nvidia", model: "nvidia/llama-3.2-nemoretriever-300m-embed-v1" }, retriever: { type: "hybrid", retrieval_type: "hybrid", top_k: 7, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: true, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
  recursive: { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.recursive }, retriever: { type: "hybrid", retrieval_type: "hybrid", top_k: 5, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
  chapter: { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.chapter_based }, retriever: { type: "hybrid", retrieval_type: "hybrid", top_k: 5, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
  sentence_window: { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.sentence_window }, retriever: { type: "dense", retrieval_type: "dense", top_k: 5, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
};

export function useConfig() {
  const [config, setConfig] = useState(DEFAULTS);
  const [step,   setStep]   = useState(0);
  const TOTAL_STEPS = 4; // upload, chunking, embedding, retrieval, llm/memory

  const updateSection = (section) => (val) =>
    setConfig((c) => ({ ...c, [section]: { ...c[section], ...val } }));

  return {
    config,
    step,
    TOTAL_STEPS,
    updateChunking:    updateSection("chunker"),
updateEmbedding:   updateSection("embedder"),
updateRetrieval:   updateSection("retriever"),
updateLLM:         updateSection("llm"),
updateMemory:      updateSection("memory"),
    applyPreset: (name) => setConfig(PRESETS[name] ?? DEFAULTS),
    nextStep: () => setStep((s) => Math.min(s + 1, TOTAL_STEPS)),
    prevStep: () => setStep((s) => Math.max(s - 1, 0)),
  };
}
