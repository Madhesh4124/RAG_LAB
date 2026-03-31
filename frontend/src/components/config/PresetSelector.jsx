const PRESETS = [
  { key: "fast",     label: "⚡ Fast",     desc: "Small chunks, quick answers. Less accurate." },
  { key: "balanced", label: "⚖️ Balanced", desc: "Good mix of speed and accuracy." },
  { key: "accurate", label: "🎯 Accurate", desc: "Semantic chunking + stronger Hugging Face embeddings. Slower but better quality." },
];

export default function PresetSelector({ onSelect, current }) {
  return (
    <div className="mb-4">
      <p className="text-xs text-gray-500 font-medium mb-2 uppercase tracking-wide">Quick Presets</p>
      <div className="flex gap-2 flex-wrap">
        {PRESETS.map(({ key, label, desc }) => (
          <button
            key={key}
            onClick={() => onSelect(key)}
            title={desc}
            className="px-3 py-1.5 rounded-lg border text-sm font-medium transition-all
              hover:border-blue-400 hover:bg-blue-50 border-gray-200 text-gray-600"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
