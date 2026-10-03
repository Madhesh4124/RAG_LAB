const PRESETS = [
  { key: "fast",     label: "⚡ Fast",     desc: "Small chunks, quick answers. Less accurate." },
  { key: "balanced", label: "⚖️ Balanced", desc: "Good mix of speed and accuracy." },
  { key: "accurate", label: "🎯 Accurate", desc: "Semantic chunking + stronger Hugging Face embeddings. Slower but better quality." },
  { key: "recursive", label: "🔁 Recursive", desc: "Paragraph and sentence-aware chunking." },
  { key: "chapter", label: "📖 Chapter", desc: "Large chapter-sized sections with line overlap." },
  { key: "sentence_window", label: "🪟 Window", desc: "Sentence-level chunks with a context window." },
];

export default function PresetSelector({ onSelect, current }) {
  return (
    <div className="flex flex-col sm:items-end gap-1.5">
      <p className="text-[10px] font-semibold text-white/45 uppercase tracking-wider">Quick Presets</p>
      <div className="flex gap-1.5 flex-wrap">
        {PRESETS.map(({ key, label, desc }) => (
          <button
            key={key}
            type="button"
            onClick={() => onSelect(key)}
            title={desc}
            className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all duration-200
              ${current === key
                ? "bg-accent-violet/20 border-accent-violet text-white shadow-[0_0_12px_rgba(221,112,11,0.3)]"
                : "bg-surface-1/90 border-white/[0.08] text-white/75 hover:bg-white/[0.08] hover:border-white/20 hover:text-white"
              }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
