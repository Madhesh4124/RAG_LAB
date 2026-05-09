import axios from "axios";

const rawEnvBaseUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").trim();
const resolvedBaseUrl = rawEnvBaseUrl;

export const BASE_URL = resolvedBaseUrl.replace(/\/+$/, "");
export const api = axios.create({ baseURL: BASE_URL, withCredentials: true });

// ── Auth ────────────────────────────────────────────────────────
export const signup = (payload) => api.post("/api/auth/signup", payload);
export const login = (payload) => api.post("/api/auth/login", payload);
export const logout = () => api.post("/api/auth/logout");
export const getMe = () => api.get("/api/auth/me");

// ── Documents ──────────────────────────────────────────────────
export const uploadDocument = (formData, onProgress) =>
  api.post("/api/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) =>
      onProgress?.(Math.round((e.loaded * 100) / e.total)),
  });

export const getChunks = (docId, configId) =>
  api.get(`/api/documents/${docId}/chunks`, {
    params: configId ? { config_id: configId } : {}
  });

export const listDocuments = (params = {}) => api.get("/api/documents/list", { params });
export const searchDocuments = (query, limit = 50) =>
  api.get("/api/documents/search", { params: { query, limit } });
export const deleteDocument = (docId) => api.delete(`/api/documents/${docId}`);

// ── Config ──────────────────────────────────────────────────────
export const saveConfig  = (cfg)      => api.post("/api/config", cfg);
export const getBestPreset = () => api.get("/api/config/best-preset");
export const applyBestPreset = (payload) => api.post("/api/config/best-preset/apply", payload);

export const prepareChatSession = (payload) => api.post("/api/chat/prepare", payload);
export const getIndexStatus = (jobId) => api.get(`/api/documents/index-status/${jobId}`);

// ── Admin ──────────────────────────────────────────────────────
export const listChromaRoots = () => api.get("/api/admin/chroma");
export const viewChromaCollection = (collectionName) => api.get(`/api/admin/chroma/collections/${collectionName}`);
export const deleteChromaCollection = (collectionName, rootPath = null) =>
  api.delete(`/api/admin/chroma/collections/${collectionName}`, { params: rootPath ? { root_path: rootPath } : {} });
export const clearChromaRoot = (rootPath = null) =>
  api.delete("/api/admin/chroma/root", { params: rootPath ? { root_path: rootPath } : {} });

// ── Compare ─────────────────────────────────────────────────────
export const compareConfigs = (payload) => api.post("/compare/run", payload);
export const compareIndex = (payload) => api.post("/compare/index", payload);
export const clearChromaDb = () => api.post("/compare/clear-chromadb");
export const scoreMessage = (messageId) => api.post("/api/evaluation/score", { message_id: messageId });
export const getEvaluationReport = (payload) =>
  api.post("/api/evaluation/report", payload, {
    timeout: payload?.deep ? 30000 : 10000,
  });

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
    config: { name: "Broad Recall", chunk_strategy: "fixed", embedding_model: "nvidia", top_k: 8, threshold: 0.3, collection_name: "nvidia_fixed" },
    answer: "RAG combines retrieval from a knowledge base with generation from an LLM.",
    chunks: [MOCK_CHUNKS[0].text, MOCK_CHUNKS[1].text],
    scores: [0.91, 0.87],
    latency_ms: 820,
    avg_similarity: 0.89,
    chunk_count: 2,
  },
  {
    config: { name: "Precision Focus", chunk_strategy: "semantic", embedding_model: "huggingface", top_k: 3, threshold: 0.7, collection_name: "huggingface_semantic" },
    answer: "RAG retrieves relevant chunks and then grounds model output in that context.",
    chunks: [MOCK_CHUNKS[2].text],
    scores: [0.93],
    latency_ms: 1200,
    avg_similarity: 0.93,
    chunk_count: 1,
  },
  {
    config: { name: "Balanced", chunk_strategy: "recursive", embedding_model: "google", top_k: 5, threshold: 0.5, collection_name: "google_recursive" },
    answer: "RAG improves factuality by requiring answers to be based on retrieved evidence.",
    chunks: [MOCK_CHUNKS[0].text, MOCK_CHUNKS[2].text],
    scores: [0.89, 0.84],
    latency_ms: 2100,
    avg_similarity: 0.865,
    chunk_count: 2,
  },
];
export const sendMessage = (payload) => api.post("/api/chat/", payload);
