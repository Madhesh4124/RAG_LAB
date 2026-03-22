import { Card } from "../common/index";

const STRATEGIES = [
  {
    key: "fixed_size",
    label: "Fixed Size",
    icon: "📏",
    desc: "Splits text into equal-sized chunks by character count.",
    pros:  ["Predictable chunk sizes", "Fast to compute"],
    cons:  ["May split mid-sentence", "Ignores meaning"],
    bestFor: "General purpose, quick experiments",
  },
  {
    key: "semantic",
    label: "Semantic",
    icon: "🧠",
    desc: "Groups sentences by meaning using embeddings.",
    pros:  ["Respects context", "Better retrieval quality"],
    cons:  ["Slower", "Requires embedding model"],
    bestFor: "Narrative text, storybooks, articles",
  },
  {
    key: "chapter_based",
    label: "Chapter-Based",
    icon: "📖",
    desc: "Splits at detected chapter/section headings.",
    pros:  ["Natural boundaries", "Great for books"],
    cons:  ["Needs clear headings", "Uneven chunk sizes"],
    bestFor: "Books, structured documents",
  },
];

export default function ChunkingStep({ config, onChange }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Chunking Strategy</h2>
        <p className="text-sm text-gray-500">How should your document be split into pieces?</p>
      </div>

      {/* Strategy cards */}
      <div className="grid gap-3 sm:grid-cols-3">
        {STRATEGIES.map((s) => (
          <Card key={s.key} selected={config.strategy === s.key} onClick={() => onChange({ strategy: s.key })}>
            <div className="text-2xl mb-1">{s.icon}</div>
            <p className="font-semibold text-sm text-gray-800">{s.label}</p>
            <p className="text-xs text-gray-500 mt-1 mb-2">{s.desc}</p>
            <ul className="space-y-0.5">
              {s.pros.map((p) => <li key={p} className="text-xs text-green-600">✓ {p}</li>)}
              {s.cons.map((c) => <li key={c} className="text-xs text-orange-500">⚠ {c}</li>)}
            </ul>
            <p className="text-xs text-gray-400 mt-2">Best for: {s.bestFor}</p>
          </Card>
        ))}
      </div>

      {/* Parameters — only show for fixed_size */}
      {config.strategy === "fixed_size" && (
        <div className="grid gap-4 sm:grid-cols-2 mt-2">
          <SliderParam
            label="Chunk Size"
            value={config.chunk_size}
            min={128} max={2048} step={128}
            hint="characters per chunk"
            onChange={(v) => onChange({ chunk_size: v })}
          />
          <SliderParam
            label="Overlap"
            value={config.overlap}
            min={0} max={200} step={10}
            hint="shared characters between chunks"
            onChange={(v) => onChange({ overlap: v })}
          />
        </div>
      )}
    </div>
  );
}

function SliderParam({ label, value, min, max, step, hint, onChange }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-blue-600 font-mono">{value}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-blue-600"
      />
      <p className="text-xs text-gray-400">{hint}</p>
    </div>
  );
}
