import { Card } from "../common/index";

const REGEX_OPTIONS = [
  { value: "\\n\\n+", label: "Paragraph breaks (\\n\\n+)" },
  { value: "(?<=[.!?])\\s+", label: "Sentence endings ((?<=[.!?])\\s+)" },
  { value: "^\\n(?=[A-Z][a-z]+:)", label: "Dialogue (^\\n(?=[A-Z][a-z]+:))" },
];

const DEFAULT_RECURSIVE_SEPARATORS = ["\n\n", "\n", "(?<=[.!?])\\s+", " "];

const STRATEGY_DEFAULTS = {
  fixed_size: { type: "fixed_size", chunk_size: 512, overlap: 50 },
  recursive: {
    type: "recursive",
    chunk_size: 512,
    overlap: 50,
    min_chunk_size: 100,
    separators: DEFAULT_RECURSIVE_SEPARATORS,
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
  const recursiveSeparators = Array.isArray(config.separators) && config.separators.length > 0
    ? config.separators
    : DEFAULT_RECURSIVE_SEPARATORS;

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
            onClick={() => onChange(STRATEGY_DEFAULTS[s.key] ?? { type: s.key })}
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

      {config.type === "recursive" && (
        <div className="grid gap-4 sm:grid-cols-2 mt-2">
          <SliderParam
            label="Min Chunk Size"
            value={config.min_chunk_size ?? 100}
            min={10} max={512} step={10}
            hint="minimum characters allowed before a split"
            onChange={(v) => onChange({ min_chunk_size: v })}
          />
          <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3">
            <input
              id="recursive-overlap"
              type="checkbox"
              checked={config.apply_overlap_recursively ?? true}
              onChange={(e) => onChange({ apply_overlap_recursively: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="recursive-overlap" className="text-sm text-gray-700">
              Apply overlap recursively
            </label>
          </div>
          <div className="sm:col-span-2 space-y-3 rounded-xl border border-gray-200 bg-white p-4">
            <div>
              <p className="text-sm font-medium text-gray-700">Separators</p>
              <p className="text-xs text-gray-400">Edit the separator list used from coarsest to finest.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                { label: "Paragraph separator", value: recursiveSeparators[0] ?? DEFAULT_RECURSIVE_SEPARATORS[0] },
                { label: "Line separator", value: recursiveSeparators[1] ?? DEFAULT_RECURSIVE_SEPARATORS[1] },
                { label: "Sentence regex", value: recursiveSeparators[2] ?? DEFAULT_RECURSIVE_SEPARATORS[2] },
                { label: "Word separator", value: recursiveSeparators[3] ?? DEFAULT_RECURSIVE_SEPARATORS[3] },
              ].map((field, index) => (
                <SeparatorField
                  key={field.label}
                  label={field.label}
                  value={field.value}
                  onChange={(nextValue) => {
                    const nextSeparators = [...recursiveSeparators];
                    nextSeparators[index] = nextValue;
                    onChange({ separators: nextSeparators });
                  }}
                />
              ))}
            </div>
          </div>
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
          <SliderParam
            label="Min Chunk Size"
            value={config.min_chunk_size ?? 100}
            min={10} max={512} step={10}
            hint="minimum characters before a soft split"
            onChange={(v) => onChange({ min_chunk_size: v })}
          />
          <SliderParam
            label="Similarity Threshold"
            value={config.similarity_threshold ?? 0.7}
            min={0.5} max={0.9} step={0.01}
            hint="lower values split more aggressively"
            onChange={(v) => onChange({ similarity_threshold: v })}
          />
          <SliderParam
            label="Hard Split Threshold"
            value={config.hard_split_threshold ?? 0.4}
            min={0.1} max={0.8} step={0.01}
            hint="split immediately below this similarity"
            onChange={(v) => onChange({ hard_split_threshold: v })}
          />
          <SliderParam
            label="Overlap Sentences"
            value={config.overlap_sentences ?? 1}
            min={0} max={3} step={1}
            hint="trailing sentences carried into the next chunk"
            onChange={(v) => onChange({ overlap_sentences: v })}
          />
        </div>
      )}

      {config.type === "chapter_based" && (
        <div className="grid gap-4 sm:grid-cols-2 mt-2">
          <SliderParam
            label="Max Chunk Size"
            value={config.max_chunk_size ?? 1024}
            min={1024} max={2048} step={256}
            hint="maximum characters per chapter chunk"
            onChange={(v) => onChange({ max_chunk_size: v })}
          />
          <SliderParam
            label="Overlap Lines"
            value={config.overlap_lines ?? 1}
            min={0} max={2} step={1}
            hint="extra lines carried across chapter boundaries"
            onChange={(v) => onChange({ overlap_lines: v })}
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

function SeparatorField({ label, value, onChange }) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <input
        type="text"
        value={encodeSeparatorValue(value)}
        onChange={(e) => onChange(decodeSeparatorValue(e.target.value))}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none"
      />
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

function encodeSeparatorValue(value) {
  if (value === "\n\n") return "\\n\\n";
  if (value === "\n") return "\\n";
  if (value === " ") return "[space]";
  return value ?? "";
}

function decodeSeparatorValue(value) {
  if (value === "\\n\\n") return "\n\n";
  if (value === "\\n") return "\n";
  if (value === "[space]") return " ";
  return value;
}
