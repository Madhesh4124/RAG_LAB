import { useState } from "react";

// Color palette — each chunk gets a rotating color
const CHUNK_COLORS = [
  { bg: "bg-blue-100",  border: "border-blue-400",  text: "text-blue-800",  ring: "ring-blue-300"  },
  { bg: "bg-purple-100",border: "border-purple-400", text: "text-purple-800",ring: "ring-purple-300"},
  { bg: "bg-green-100", border: "border-green-400",  text: "text-green-800", ring: "ring-green-300" },
  { bg: "bg-pink-100",  border: "border-pink-400",   text: "text-pink-800",  ring: "ring-pink-300"  },
  { bg: "bg-yellow-100",border: "border-yellow-400", text: "text-yellow-800",ring: "ring-yellow-300"},
];

export default function ChunkVisualizer({ chunks = [], loading }) {
  const [selectedId, setSelectedId] = useState(null);

  const selected = chunks.find((c) => c.id === selectedId);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <div className="text-center space-y-2">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-blue-500 mx-auto" />
          <p className="text-sm">Generating chunks…</p>
        </div>
      </div>
    );
  }

  if (!chunks.length) {
    return (
      <div className="flex items-center justify-center h-64 rounded-xl border-2 border-dashed border-gray-200 text-gray-400">
        <p className="text-sm">Upload a document and configure chunking to see the preview.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">

      {/* ── Left panel: chunk blocks ──────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white overflow-y-auto max-h-[600px] p-4 space-y-2">
        <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-3">
          {chunks.length} chunks — click to inspect
        </p>

        {chunks.map((chunk, i) => {
          const color   = CHUNK_COLORS[i % CHUNK_COLORS.length];
          const isSelected = chunk.id === selectedId;
          const hasOverlapPrev = !!chunk.overlap_prev;
          const hasOverlapNext = !!chunk.overlap_next;

          return (
            <div key={chunk.id} onClick={() => setSelectedId(isSelected ? null : chunk.id)}>

              {/* Overlap indicator — top */}
              {hasOverlapPrev && (
                <div className="text-[10px] text-orange-500 font-medium pl-2 -mb-1">
                  ⟵ {chunk.overlap_prev}ch overlap with previous
                </div>
              )}

              {/* Chunk block */}
              <div className={`rounded-lg border-l-4 px-3 py-2 cursor-pointer transition-all
                ${color.bg} ${color.border}
                ${isSelected ? `ring-2 ${color.ring} shadow-sm` : "hover:shadow-sm"}
              `}>
                <div className="flex justify-between items-start mb-1">
                  <span className={`text-[10px] font-mono font-bold ${color.text}`}>
                    #{chunk.sequence_num + 1} · {chunk.id.slice(0, 6)}
                  </span>
                  <span className="text-[10px] text-gray-400">
                    {chunk.start_char}–{chunk.end_char}
                  </span>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed line-clamp-3">
                  {chunk.text}
                </p>
              </div>

              {/* Overlap indicator — bottom */}
              {hasOverlapNext && (
                <div className="text-[10px] text-orange-500 font-medium pl-2 -mt-1">
                  {chunk.overlap_next}ch overlap with next ⟶
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Right panel: selected chunk detail ───────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white p-4">
        {selected ? (
          <ChunkDetail chunk={selected} index={chunks.indexOf(selected)} color={CHUNK_COLORS[chunks.indexOf(selected) % CHUNK_COLORS.length]} />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-300">
            <div className="text-center">
              <div className="text-4xl mb-2">👈</div>
              <p className="text-sm">Select a chunk to see details</p>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}

function ChunkDetail({ chunk, index, color }) {
  const charCount  = chunk.end_char - chunk.start_char;
  const approxTokens = Math.round(charCount / 4); // rough approximation

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className={`w-3 h-3 rounded-full border-2 ${color.border} ${color.bg}`} />
        <h3 className="font-semibold text-gray-800">Chunk #{index + 1}</h3>
      </div>

      {/* Metadata grid */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: "Chunk ID",     value: chunk.id },
          { label: "Position",     value: `${chunk.start_char} → ${chunk.end_char}` },
          { label: "Characters",   value: charCount },
          { label: "Approx Tokens", value: `~${approxTokens}` },
          chunk.overlap_prev && { label: "Overlap Prev", value: `${chunk.overlap_prev}ch` },
          chunk.overlap_next && { label: "Overlap Next", value: `${chunk.overlap_next}ch` },
        ].filter(Boolean).map(({ label, value }) => (
          <div key={label} className="rounded-lg bg-gray-50 p-2">
            <p className="text-[10px] text-gray-400 uppercase tracking-wide">{label}</p>
            <p className="text-xs font-mono text-gray-700 mt-0.5 truncate">{value}</p>
          </div>
        ))}
      </div>

      {/* Full text */}
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Full Text</p>
        <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 max-h-52 overflow-y-auto">
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{chunk.text}</p>
        </div>
      </div>
    </div>
  );
}
