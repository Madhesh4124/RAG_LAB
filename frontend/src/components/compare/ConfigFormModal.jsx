import { useMemo, useState } from "react";
import { Badge, Button } from "../common/index";

export default function ConfigFormModal({ onSave, onCancel, existingNames = [], isDisabled }) {
  const [name, setName] = useState("");
  const [chunkStrategy, setChunkStrategy] = useState("fixed");
  const [embeddingModel, setEmbeddingModel] = useState("nvidia");
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
            <p className="text-sm text-gray-500">Only name, top_k, and similarity threshold are configurable.</p>
          </div>
          <Badge color="gray">MVP</Badge>
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
              onChange={(e) => setChunkStrategy(e.target.value)}
              disabled={isDisabled}
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="fixed">Fixed Size</option>
              <option value="semantic">Semantic</option>
              <option value="recursive">Recursive</option>
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
              <option value="nvidia">NVIDIA (nvidia/nv-embed-v1)</option>
              <option value="huggingface">HuggingFace (sentence-transformers/all-MiniLM-L6-v2)</option>
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
