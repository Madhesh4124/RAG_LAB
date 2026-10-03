import { useState, useEffect, useCallback } from "react";

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
  embedder:    { provider: "nvidia", model: "nvidia/nemotron-3-embed-1b" },
  vectorstore: { type: "chroma", collection_name: "my_collection" },
  retriever:   { type: "hybrid", retrieval_type: "hybrid", top_k: 5, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" },
  llm:         { provider: "gemini", model: "gemini-2.5-flash" },
  memory:      { type: "buffer", max_turns: 5, max_turns_before_summary: 5 },
};

const PRESETS = {
  fast:     { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.fixed_size, chunk_size: 256, overlap: 20 }, retriever: { type: "hybrid", retrieval_type: "hybrid", top_k: 3, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
  balanced: { ...DEFAULTS },
  accurate: { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.semantic, max_chunk_size: 1024, similarity_threshold: 0.7, overlap_sentences: 1 }, embedder: { provider: "nvidia", model: "nvidia/nemotron-3-embed-1b" }, retriever: { type: "hybrid", retrieval_type: "hybrid", top_k: 7, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: true, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
  recursive: { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.recursive }, retriever: { type: "hybrid", retrieval_type: "hybrid", top_k: 5, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
  chapter: { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.chapter_based }, retriever: { type: "hybrid", retrieval_type: "hybrid", top_k: 5, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
  sentence_window: { ...DEFAULTS, chunker: { ...CHUNKER_DEFAULTS.sentence_window }, retriever: { type: "dense", retrieval_type: "dense", top_k: 5, similarity_threshold: 0.0, alpha: 0.7, lambda_mult: 0.5, reranker_enabled: false, reranker_provider: "huggingface_api", reranker_model: "BAAI/bge-reranker-base" } },
};

const CONFIG_STORAGE_KEY = "rag_lab_pipeline_config_v2";

function loadSavedConfig() {
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!raw) return { config: DEFAULTS, step: 0 };
    const parsed = JSON.parse(raw);
    return {
      config: parsed?.config || DEFAULTS,
      step: typeof parsed?.step === "number" ? parsed.step : 0,
    };
  } catch {
    return { config: DEFAULTS, step: 0 };
  }
}

export function useConfig() {
  const [state, setState] = useState(loadSavedConfig);
  const TOTAL_STEPS = 4; // upload, chunking, embedding, retrieval, llm/memory

  useEffect(() => {
    try {
      localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.error("Failed to save pipeline config", e);
    }
  }, [state]);

  const updateSection = useCallback((section) => (val) => {
    setState((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        [section]: { ...prev.config[section], ...val },
      },
    }));
  }, []);

  const applyPreset = useCallback((name) => {
    setState((prev) => ({
      ...prev,
      config: PRESETS[name] ?? DEFAULTS,
    }));
  }, []);

  const nextStep = useCallback(() => {
    setState((prev) => ({ ...prev, step: Math.min(prev.step + 1, TOTAL_STEPS) }));
  }, []);

  const prevStep = useCallback(() => {
    setState((prev) => ({ ...prev, step: Math.max(prev.step - 1, 0) }));
  }, []);

  const resetConfig = useCallback(() => {
    setState({ config: DEFAULTS, step: 0 });
  }, []);

  return {
    config: state.config,
    step: state.step,
    TOTAL_STEPS,
    updateChunking:  updateSection("chunker"),
    updateEmbedding: updateSection("embedder"),
    updateRetrieval: updateSection("retriever"),
    updateLLM:       updateSection("llm"),
    updateMemory:    updateSection("memory"),
    applyPreset,
    nextStep,
    prevStep,
    resetConfig,
  };
}
