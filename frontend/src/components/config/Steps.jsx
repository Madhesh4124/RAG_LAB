// ── EmbeddingStep ────────────────────────────────────────────────
import { Card } from "../common/index";

const MODELS = [
  { key: "google",      provider: "google", model: "models/gemini-embedding-2-preview", label: "Google Gemini", icon: "🌐", note: "gemini-embedding-2-preview. Default choice." },
  { key: "nvidia",      provider: "nvidia", model: "nvidia",                           label: "Nvidia",        icon: "⚡", note: "High performance embeddings." },
  { key: "huggingface", provider: "huggingface", model: "sentence-transformers/all-MiniLM-L6-v2", label: "HuggingFace",   icon: "🤗", note: "Open source models." },
];

export function EmbeddingStep({ config, onChange }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Embedding Model</h2>
        <p className="text-sm text-gray-500">Converts text chunks into vectors for similarity search.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {MODELS.map((m) => (
          <Card key={m.key} selected={config.provider === m.provider} onClick={() => onChange({ provider: m.provider, model: m.model })}>
            <div className="text-2xl mb-1">{m.icon}</div>
            <p className="font-semibold text-sm text-gray-800">{m.label}</p>
            <p className="text-xs text-gray-400 mt-0.5">{m.provider}</p>
            <p className="text-xs text-gray-500 mt-2">{m.note}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── VectorStoreStep ──────────────────────────────────────────────
const STORES = [
  { key: "chroma", label: "ChromaDB",  icon: "🗄️", note: "Simple, persistent, great for demos. Default choice." },
  { key: "faiss",  label: "FAISS",     icon: "⚡", note: "Fast in-memory search. No persistence by default." },
];

export function VectorStoreStep({ config, onChange }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Vector Store</h2>
        <p className="text-sm text-gray-500">Where embedded chunks are stored and searched.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {STORES.map((s) => (
          <Card key={s.key} selected={config.type === s.key} onClick={() => onChange({ type: s.key })}>
            <div className="text-2xl mb-1">{s.icon}</div>
            <p className="font-semibold text-sm text-gray-800">{s.label}</p>
            <p className="text-xs text-gray-500 mt-2">{s.note}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── RetrievalStep ────────────────────────────────────────────────
export function RetrievalStep({ config, onChange }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Retrieval Parameters</h2>
        <p className="text-sm text-gray-500">How many chunks to fetch and how strict the similarity filter is.</p>
      </div>

      {/* Top-K */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700">Top-K chunks</span>
          <span className="text-blue-600 font-mono">{config.top_k}</span>
        </div>
        <input type="range" min={1} max={10} step={1} value={config.top_k}
          onChange={(e) => onChange({ top_k: Number(e.target.value) })}
          className="w-full accent-blue-600" />
        <p className="text-xs text-gray-400">How many chunks to pass to the LLM</p>
      </div>

      {/* Similarity threshold */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700">Similarity Threshold</span>
          <span className="text-blue-600 font-mono">{config.similarity_threshold}</span>
        </div>
        <input type="range" min={0.1} max={1.0} step={0.05} value={config.similarity_threshold}
          onChange={(e) => onChange({ similarity_threshold: Number(e.target.value) })}
          className="w-full accent-blue-600" />
        <p className="text-xs text-gray-400">Chunks below this score are discarded</p>
      </div>

      {/* Summary box */}
      <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 text-xs text-gray-600 space-y-1">
        <p className="font-semibold text-gray-700">📋 Config Summary</p>
        <p>Will retrieve up to <strong>{config.top_k} chunks</strong> with similarity ≥ <strong>{config.similarity_threshold}</strong></p>
      </div>
    </div>
  );
}
