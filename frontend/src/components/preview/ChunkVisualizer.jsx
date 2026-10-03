import React, { useState } from 'react';

// Frozen Mist rotating palette for chunks
const CHUNK_COLORS = [
  { bg: "bg-[#DD700B]/[0.08]", border: "border-l-[#DD700B]", text: "text-accent-violet-light", ring: "ring-[#DD700B]/50" },
  { bg: "bg-[#7C7D75]/[0.12]", border: "border-l-[#ADACA7]",   text: "text-[#FCF8D8]",          ring: "ring-[#ADACA7]/40" },
  { bg: "bg-white/[0.04]",     border: "border-l-[#D9DADF]/60",text: "text-[#D9DADF]",          ring: "ring-[#D9DADF]/40" },
  { bg: "bg-[#DD700B]/[0.10]", border: "border-l-[#F07D18]",   text: "text-white",              ring: "ring-[#F07D18]/50" },
  { bg: "bg-[#7C7D75]/[0.18]", border: "border-l-[#7C7D75]",   text: "text-[#FCF8D8]",          ring: "ring-[#7C7D75]/50" },
];

export default function ChunkVisualizer({ chunks = [], loading, error }) {
  const [selectedId, setSelectedId] = useState(null);

  const chunkList = Array.isArray(chunks) ? chunks : chunks?.chunks || chunks?.data || [];
  const selected = chunkList.find((c) => c.id === selectedId);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-80 rounded-2xl border border-white/10 bg-surface-1/80 text-white/60">
        <div className="text-center space-y-3">
          <div className="h-9 w-9 animate-spin rounded-full border-2 border-white/10 border-t-accent-violet mx-auto" />
          <p className="text-sm font-medium text-[#FCF8D8]">Generating and indexing chunks…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-80 rounded-2xl border border-red-500/20 bg-red-500/[0.08] text-red-400 p-6">
        <div className="text-center space-y-2 max-w-md">
          <p className="text-sm font-bold">⚠️ Error loading chunks</p>
          <p className="text-xs text-red-300/80">{error}</p>
        </div>
      </div>
    );
  }

  if (!chunkList.length) {
    return (
      <div className="flex items-center justify-center h-80 rounded-2xl border border-dashed border-white/10 bg-surface-1/50 text-white/50 p-6">
        <p className="text-sm">Upload a document and configure chunking to see the preview.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full items-start">
      {/* ── Left panel: chunk blocks ──────────────────────────── */}
      <div className="rounded-2xl border border-white/10 bg-surface-1/90 backdrop-blur-sm overflow-y-auto max-h-[700px] p-5 space-y-3 shadow-lg">
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <p className="text-xs text-[#ADACA7] font-semibold uppercase tracking-wider">
            {chunkList.length} Chunks — Click to inspect
          </p>
          <span className="text-[11px] text-white/40 font-mono">Sequential flow</span>
        </div>

        {chunkList.map((chunk, i) => {
          const color = CHUNK_COLORS[i % CHUNK_COLORS.length];
          const isSelected = chunk.id === selectedId;
          const hasOverlapPrev = !!chunk.overlap_prev;
          const hasOverlapNext = !!chunk.overlap_next;

          return (
            <div key={chunk.id} onClick={() => setSelectedId(isSelected ? null : chunk.id)} className="space-y-1">
              {/* Overlap indicator — top */}
              {hasOverlapPrev && (
                <div className="text-[10px] text-accent-violet-light font-mono font-medium pl-3">
                  ⟵ {chunk.overlap_prev}ch overlap with previous
                </div>
              )}

              {/* Chunk block */}
              <div
                className={`rounded-xl border-l-[3.5px] border border-white/[0.06] px-4 py-3 cursor-pointer transition-all duration-300
                  ${color.bg} ${color.border}
                  ${isSelected
                    ? `ring-2 ${color.ring} bg-surface-2 shadow-lg border-white/20 translate-x-1`
                    : "hover:bg-surface-2/60 hover:border-white/15"
                  }
                `}
              >
                <div className="flex justify-between items-start mb-1.5">
                  <span className={`text-[11px] font-mono font-bold ${color.text}`}>
                    #{chunk.sequence_num !== undefined ? chunk.sequence_num + 1 : i + 1} · {String(chunk.id).slice(0, 8)}
                  </span>
                  <span className="text-[10px] font-mono text-white/45 bg-white/[0.04] px-2 py-0.5 rounded-md border border-white/[0.05]">
                    {chunk.start_char}–{chunk.end_char}
                  </span>
                </div>
                <p className="text-xs text-[#D9DADF] leading-relaxed line-clamp-3">
                  {chunk.text}
                </p>
              </div>

              {/* Overlap indicator — bottom */}
              {hasOverlapNext && (
                <div className="text-[10px] text-accent-violet-light font-mono font-medium pl-3">
                  {chunk.overlap_next}ch overlap with next ⟶
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Right panel: selected chunk detail ───────────────── */}
      <div className="rounded-2xl border border-white/10 bg-surface-1/90 backdrop-blur-sm p-6 sticky top-24 max-h-[700px] overflow-y-auto shadow-lg">
        {selected ? (
          <ChunkDetail
            chunk={selected}
            index={chunkList.indexOf(selected)}
            color={CHUNK_COLORS[chunkList.indexOf(selected) % CHUNK_COLORS.length]}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full min-h-[380px] text-center p-8">
            <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/10 flex items-center justify-center text-2xl mb-3 shadow-inner">
              👈
            </div>
            <p className="text-base font-bold text-[#FCF8D8]">Select a chunk to inspect</p>
            <p className="text-xs text-[#D9DADF]/60 mt-1 max-w-xs leading-relaxed">
              Click any chunk in the sequential list on the left to inspect character ranges, token counts, and full content.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function ChunkDetail({ chunk, index, color }) {
  const charCount = (chunk.end_char ?? 0) - (chunk.start_char ?? 0);
  const approxTokens = Math.round(charCount / 4);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className={`w-3.5 h-3.5 rounded-full ${color.bg} border-2 ${color.border.replace('border-l-', 'border-')}`} />
          <h3 className="font-bold text-lg text-[#FCF8D8]">Chunk #{index + 1}</h3>
        </div>
        <span className="text-[10px] font-mono text-accent-violet-light bg-accent-violet/15 px-2.5 py-1 rounded-lg border border-accent-violet/30 font-semibold">
          Active Selection
        </span>
      </div>

      {/* Metadata grid */}
      <div className="grid grid-cols-2 gap-2.5">
        {[
          { label: "Chunk ID", value: chunk.id },
          { label: "Position", value: `${chunk.start_char} → ${chunk.end_char}` },
          { label: "Characters", value: `${charCount} chars` },
          { label: "Approx Tokens", value: `~${approxTokens} tokens` },
          chunk.overlap_prev && { label: "Overlap Prev", value: `${chunk.overlap_prev} chars` },
          chunk.overlap_next && { label: "Overlap Next", value: `${chunk.overlap_next} chars` },
        ].filter(Boolean).map(({ label, value }) => (
          <div key={label} className="rounded-xl bg-surface-2/80 border border-white/[0.07] p-3">
            <p className="text-[10px] text-[#ADACA7] font-semibold uppercase tracking-wider">{label}</p>
            <p className="text-xs font-mono text-[#FCF8D8] mt-1 font-semibold truncate">{value}</p>
          </div>
        ))}
      </div>

      {/* Full text */}
      <div className="space-y-2">
        <p className="text-xs text-[#ADACA7] font-semibold uppercase tracking-wider">Full Verbatim Text</p>
        <div className="rounded-xl bg-surface-2/60 border border-white/[0.08] p-4 max-h-72 overflow-y-auto">
          <p className="text-xs text-[#D9DADF] leading-relaxed whitespace-pre-wrap font-mono select-text">
            {chunk.text}
          </p>
        </div>
      </div>
    </div>
  );
}
