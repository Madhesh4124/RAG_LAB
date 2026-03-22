import axios from "axios";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: BASE });

// ── Documents ──────────────────────────────────────────────────
export const uploadDocument = (formData, onProgress) =>
  api.post("/api/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) =>
      onProgress?.(Math.round((e.loaded * 100) / e.total)),
  });

export const getChunks = (docId, config) =>
  api.get(`/api/documents/${docId}/chunks`, { params: config });

// ── Config ──────────────────────────────────────────────────────
export const saveConfig  = (cfg)      => api.post("/api/config", cfg);
export const listConfigs = ()         => api.get("/api/config/list");

// ── Compare ─────────────────────────────────────────────────────
export const compareConfigs = (payload) => api.post("/api/compare", payload);

// ── MOCK DATA (delete once backend is ready) ────────────────────
export const MOCK_CHUNKS = [
  {
    id: "c001", sequence_num: 0,
    text: "Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do.",
    start_char: 0, end_char: 104, overlap_next: 20,
  },
  {
    id: "c002", sequence_num: 1,
    text: "once or twice she had peeped into the book her sister was reading, but it had no pictures or conversations in it,",
    start_char: 84, end_char: 196, overlap_prev: 20, overlap_next: 15,
  },
  {
    id: "c003", sequence_num: 2,
    text: "and what is the use of a book, thought Alice, without pictures or conversations?",
    start_char: 181, end_char: 260, overlap_prev: 15,
  },
];

export const MOCK_COMPARE_RESULTS = [
  {
    configId: "cfg1", configName: "Fast — Small Chunks",
    params: { strategy: "fixed_size", chunk_size: 256, overlap: 20, model: "nomic", top_k: 3 },
    answer: "Alice was bored sitting by the riverbank with her sister.",
    metrics: { response_time_ms: 820, chunks_retrieved: 3, avg_similarity: 0.81, token_count: 310 },
    chunks: [MOCK_CHUNKS[0]],
  },
  {
    configId: "cfg2", configName: "Balanced",
    params: { strategy: "fixed_size", chunk_size: 512, overlap: 50, model: "mxbai", top_k: 5 },
    answer: "Alice sat by the river, bored, with no interesting book in sight.",
    metrics: { response_time_ms: 1200, chunks_retrieved: 5, avg_similarity: 0.86, token_count: 430 },
    chunks: [MOCK_CHUNKS[0], MOCK_CHUNKS[1]],
  },
  {
    configId: "cfg3", configName: "Accurate — Semantic",
    params: { strategy: "semantic", chunk_size: 1024, overlap: 100, model: "openai", top_k: 7 },
    answer: "Alice was growing tired of sitting beside her sister near the bank, having nothing to read or do.",
    metrics: { response_time_ms: 2100, chunks_retrieved: 7, avg_similarity: 0.91, token_count: 580 },
    chunks: MOCK_CHUNKS,
  },
];
