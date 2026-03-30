import { Card } from "../common/index";

const REGEX_OPTIONS = [
  { value: "\\n\\n+", label: "Paragraph breaks (\\n\\n+)" },
  { value: "(?<=[.!?])\\s+", label: "Sentence endings ((?<=[.!?])\\s+)" },
  { value: "^\\n(?=[A-Z][a-z]+:)", label: "Dialogue (^\\n(?=[A-Z][a-z]+:))" },
];

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
  {
    key: "recursive",
    label: "Recursive",
    icon: "🔁",
    desc: "Splits using separator hierarchy: paragraphs → sentences → words.",
    pros:  ["Respects natural text structure", "Configurable separators"],
    cons:  ["More complex to tune"],
    bestFor: "Mixed documents, code, structured text",
  },
  {
    key: "regex",
    label: "Regex",
    icon: "🔍",
    desc: "Splits on a custom regex pattern (paragraph breaks, dialogue, etc.)",
    pros:  ["Fully customizable splits"],
    cons:  ["Requires regex knowledge"],
    bestFor: "Dialogue, scripts, custom formats",
  },
  {
    key: "sentence_window",
    label: "Sentence Window",
    icon: "🪟",
    desc: "Embeds each sentence and stores neighboring sentence context.",
    pros:  ["Precise matching", "Context-preserving generation"],
    cons:  ["More chunks to index"],
    bestFor: "QA over long prose and technical docs",
  },
];

export default function ChunkingStep({ config, onChange }) {
  const regexOptionValues = REGEX_OPTIONS.map((o) => o.value);
  const selectedRegexPattern = regexOptionValues.includes(config.pattern)
    ? config.pattern
    : "__custom__";

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Chunking Strategy</h2>
        <p className="text-sm text-gray-500">How should your document be split into pieces?</p>
      </div>

      {/* Strategy cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {STRATEGIES.map((s) => (
          <Card
            key={s.key}
            selected={config.type === s.key}
            onClick={() =>
              onChange(
                s.key === "recursive"
                  ? { type: "recursive", separators: ["\n\n", "\n", ". ", " "] }
                  : s.key === "regex"
                    ? { type: "regex", pattern: "\\n\\n+", min_chunk_size: 100 }
                    : s.key === "sentence_window"
                      ? { type: "sentence_window", window_size: 3 }
                    : { type: s.key }
              )
            }
          >
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

      {/* Parameters — only show for fixed_size/recursive */}
      {(config.type === "fixed_size" || config.type === "recursive") && (
        <div className="grid gap-4 sm:grid-cols-2 mt-2">
          <SliderParam
            label="Chunk Size"
            value={config.chunk_size ?? 512}
            min={128} max={2048} step={128}
            hint="characters per chunk"
            onChange={(v) => onChange({ chunk_size: v })}
          />
          <SliderParam
            label="Overlap"
            value={config.overlap ?? 50}
            min={0} max={200} step={10}
            hint="shared characters between chunks"
            onChange={(v) => onChange({ overlap: v })}
          />
        </div>
      )}

      {config.type === "semantic" && (
        <div className="grid gap-4 sm:grid-cols-2 mt-2">
          <SliderParam
            label="Max Chunk Size"
            value={config.max_chunk_size ?? 512}
            min={128} max={4096} step={128}
            hint="maximum characters per semantic chunk"
            onChange={(v) => onChange({ max_chunk_size: v })}
          />
        </div>
      )}

      {config.type === "regex" && (
        <div className="grid gap-4 sm:grid-cols-2 mt-2">
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700">Pattern</label>
            <select
              value={selectedRegexPattern}
              onChange={(e) => {
                const value = e.target.value;
                if (value === "__custom__") {
                  onChange({ pattern: config.pattern ?? "" });
                  return;
                }
                onChange({ pattern: value });
              }}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {REGEX_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
              <option value="__custom__">Custom pattern</option>
            </select>
            <p className="text-xs text-gray-400">Choose a preset or switch to custom regex.</p>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700">Min Chunk Size</label>
            <input
              type="number"
              min={1}
              step={1}
              value={config.min_chunk_size ?? 100}
              onChange={(e) => onChange({ min_chunk_size: Number(e.target.value) || 100 })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
            <p className="text-xs text-gray-400">Discard chunks below this character length.</p>
          </div>

          {selectedRegexPattern === "__custom__" && (
            <div className="space-y-1 sm:col-span-2">
              <label className="text-sm font-medium text-gray-700">Custom Pattern</label>
              <input
                type="text"
                value={config.pattern ?? ""}
                onChange={(e) => onChange({ pattern: e.target.value })}
                placeholder="Enter regex pattern"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none"
              />
              <p className="text-xs text-gray-400">Example: \\n\\n+ or (?&lt;=[.!?])\\s+</p>
            </div>
          )}
        </div>
      )}

      {config.type === "sentence_window" && (
        <div className="grid gap-4 sm:grid-cols-2 mt-2">
          <SliderParam
            label="Window Size"
            value={config.window_size ?? 3}
            min={1} max={7} step={1}
            hint="number of sentences in context window"
            onChange={(v) => onChange({ window_size: v })}
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
