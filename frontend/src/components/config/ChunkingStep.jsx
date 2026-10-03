import React from 'react';

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
    <div className="space-y-6">
      <div>
        <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">Chunking Strategy</h2>
        <p className="text-sm text-white/60 mt-0.5">Choose how documents are split before indexing into the vector database.</p>
      </div>

      {/* Strategy cards */}
      <div className="grid gap-3.5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
        {STRATEGIES.map((s) => {
          const isSelected = config.type === s.key;
          return (
            <div
              key={s.key}
              onClick={() => onChange(STRATEGY_DEFAULTS[s.key] ?? { type: s.key })}
              className={`relative flex flex-col justify-between p-4 rounded-2xl border transition-all duration-300 cursor-pointer text-left
                ${isSelected
                  ? "bg-accent-violet/[0.12] border-accent-violet shadow-[0_0_0_1px_rgba(221,112,11,0.5),0_8px_24px_rgba(221,112,11,0.2)]"
                  : "bg-surface-1/90 border-white/[0.08] hover:border-white/25 hover:bg-surface-2 hover:-translate-y-0.5 shadow-sm"
                }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-white/[0.06] border border-white/[0.08] flex items-center justify-center text-xl shadow-inner">
                    {s.icon}
                  </div>
                  <div
                    className={`w-4 h-4 rounded-full border flex items-center justify-center transition-all ${
                      isSelected
                        ? "border-accent-violet bg-accent-violet"
                        : "border-white/20 bg-white/[0.04]"
                    }`}
                  >
                    {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                  </div>
                </div>
                <p className="font-bold text-sm text-white tracking-tight">{s.label}</p>
                <p className="text-xs text-white/65 mt-1.5 leading-relaxed">{s.desc}</p>
                
                <div className="mt-3 pt-3 border-t border-white/[0.06] space-y-1">
                  {s.pros.map((p) => (
                    <div key={p} className="text-[11px] text-emerald-400 font-medium flex items-center gap-1.5">
                      <span className="text-emerald-400">✓</span> {p}
                    </div>
                  ))}
                  {s.cons.map((c) => (
                    <div key={c} className="text-[11px] text-amber-300/80 font-medium flex items-center gap-1.5">
                      <span className="text-amber-400">⚠</span> {c}
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-[10px] text-white/45 mt-3 pt-2.5 border-t border-white/[0.06] font-medium">
                <span className="text-white/60">Best:</span> {s.bestFor}
              </p>
            </div>
          );
        })}
      </div>

      {/* Parameters */}
      {(config.type === "fixed_size" || config.type === "recursive") && (
        <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-5 mt-4 space-y-4">
          <h3 className="text-xs font-bold text-white/70 uppercase tracking-wider">Parameters: {config.type.replace('_', ' ')}</h3>
          <div className="grid gap-4 sm:grid-cols-2">
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
        </div>
      )}

      {config.type === "recursive" && (
        <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-5 mt-4 space-y-4">
          <h3 className="text-xs font-bold text-white/70 uppercase tracking-wider">Recursive Configuration</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <SliderParam
              label="Min Chunk Size"
              value={config.min_chunk_size ?? 100}
              min={10} max={512} step={10}
              hint="minimum characters allowed before a split"
              onChange={(v) => onChange({ min_chunk_size: v })}
            />
            <div className="flex items-center gap-2.5 rounded-xl border border-white/[0.08] bg-surface-2/60 px-4 py-3">
              <input
                id="recursive-overlap"
                type="checkbox"
                checked={config.apply_overlap_recursively ?? true}
                onChange={(e) => onChange({ apply_overlap_recursively: e.target.checked })}
                className="h-4 w-4 rounded border-white/20 bg-surface-1 text-accent-violet accent-accent-violet focus:ring-accent-violet cursor-pointer"
              />
              <label htmlFor="recursive-overlap" className="text-sm font-medium text-white/80 cursor-pointer">
                Apply overlap recursively
              </label>
            </div>
            <div className="sm:col-span-2 space-y-3 rounded-xl border border-white/[0.08] bg-surface-2/40 p-4">
              <div>
                <p className="text-sm font-semibold text-white">Separators</p>
                <p className="text-xs text-white/50">Edit the separator hierarchy used from coarsest to finest.</p>
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
        </div>
      )}

      {config.type === "semantic" && (
        <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-5 mt-4 space-y-4">
          <h3 className="text-xs font-bold text-white/70 uppercase tracking-wider">Semantic Parameters</h3>
          <div className="grid gap-4 sm:grid-cols-2">
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
        </div>
      )}

      {config.type === "chapter_based" && (
        <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-5 mt-4 space-y-4">
          <h3 className="text-xs font-bold text-white/70 uppercase tracking-wider">Chapter-Based Parameters</h3>
          <div className="grid gap-4 sm:grid-cols-2">
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
        </div>
      )}

      {config.type === "regex" && (
        <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-5 mt-4 space-y-4">
          <h3 className="text-xs font-bold text-white/70 uppercase tracking-wider">Regex Pattern Configuration</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
              <label className="text-xs font-semibold text-white/70">Pattern</label>
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
                className="w-full rounded-xl border border-white/10 bg-surface-1 px-3 py-2 text-sm text-white focus:border-accent-violet outline-none"
              >
                {REGEX_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value} className="bg-surface-2 text-white">{o.label}</option>
                ))}
                <option value="__custom__" className="bg-surface-2 text-white">Custom pattern</option>
              </select>
              <p className="text-[11px] text-white/45">Choose a preset or switch to custom regex.</p>
            </div>

            <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
              <label className="text-xs font-semibold text-white/70">Min Chunk Size</label>
              <input
                type="number"
                min={1}
                step={1}
                value={config.min_chunk_size ?? 100}
                onChange={(e) => onChange({ min_chunk_size: Number(e.target.value) || 100 })}
                className="w-full rounded-xl border border-white/10 bg-surface-1 px-3 py-2 text-sm text-white focus:border-accent-violet outline-none"
              />
              <p className="text-[11px] text-white/45">Discard chunks below this character length.</p>
            </div>

            {selectedRegexPattern === "__custom__" && (
              <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07] sm:col-span-2">
                <label className="text-xs font-semibold text-white/70">Custom Pattern</label>
                <input
                  type="text"
                  value={config.pattern ?? ""}
                  onChange={(e) => onChange({ pattern: e.target.value })}
                  placeholder="Enter regex pattern"
                  className="w-full rounded-xl border border-white/10 bg-surface-1 px-3 py-2 text-sm font-mono text-white focus:border-accent-violet outline-none"
                />
                <p className="text-[11px] text-white/45">Example: \\n\\n+ or (?&lt;=[.!?])\\s+</p>
              </div>
            )}
          </div>
        </div>
      )}

      {config.type === "sentence_window" && (
        <div className="rounded-2xl border border-white/[0.08] bg-surface-1/70 p-5 mt-4 space-y-4">
          <h3 className="text-xs font-bold text-white/70 uppercase tracking-wider">Sentence Window Parameters</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <SliderParam
              label="Window Size"
              value={config.window_size ?? 3}
              min={1} max={7} step={1}
              hint="number of sentences in context window"
              onChange={(v) => onChange({ window_size: v })}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function SeparatorField({ label, value, onChange }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-semibold text-white/70">{label}</label>
      <input
        type="text"
        value={encodeSeparatorValue(value)}
        onChange={(e) => onChange(decodeSeparatorValue(e.target.value))}
        className="w-full rounded-xl border border-white/10 bg-surface-2 px-3 py-2 text-sm font-mono text-white focus:border-accent-violet focus:ring-1 focus:ring-accent-violet outline-none"
      />
    </div>
  );
}

function SliderParam({ label, value, min, max, step, hint, onChange }) {
  return (
    <div className="space-y-1.5 p-3.5 rounded-xl bg-surface-2/60 border border-white/[0.07]">
      <div className="flex justify-between items-center text-sm">
        <span className="font-semibold text-white/90">{label}</span>
        <span className="text-accent-violet-light font-mono font-bold text-xs bg-accent-violet/15 px-2.5 py-0.5 rounded-md border border-accent-violet/30">
          {value}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-violet"
      />
      <p className="text-[11px] text-white/45">{hint}</p>
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
