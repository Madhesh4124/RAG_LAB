import React from 'react';
import { useNavigate } from "react-router-dom";
import { useSession } from "../hooks/useSession";
import { Button, Badge } from "../components/common/index";
import { IconChat, IconSettings, IconCompare, IconArrowRight } from "../components/common/Icons";

const modes = [
  {
    key: "chat",
    path: "/chat",
    tag: "Standard Workspace",
    label: "Quick Chat",
    description: "Instant document QA with automated pipeline tuning and best-preset embedding defaults.",
    icon: IconChat,
    badgeColor: "amber",
    specs: [
      "Auto-chunking & indexing",
      "Streaming hybrid retrieval",
      "Source citation inspector",
      "Automated prompt routing",
    ],
    primaryAction: "Start Chat",
  },
  {
    key: "custom-chat",
    path: "/setup",
    tag: "Pipeline Architect",
    label: "Custom Pipeline",
    description: "Granular control over chunk sizes, overlap, embedding models, vector stores, and reranking parameters.",
    icon: IconSettings,
    badgeColor: "blue",
    specs: [
      "Recursive / semantic splitters",
      "Multi-provider embeddings",
      "Top-K & similarity thresholds",
      "Custom memory & LLM configs",
    ],
    primaryAction: "Configure Pipeline",
  },
  {
    key: "compare",
    path: "/compare",
    tag: "Comparison Lab",
    label: "Compare",
    description: "Run multiple RAG configurations in parallel. Benchmark retrieval quality and answer accuracy side-by-side.",
    icon: IconCompare,
    badgeColor: "emerald",
    specs: [
      "Side-by-side response diff",
      "Staging queue (up to 4 configs)",
      "Similarity score distribution",
      "Latency & token profiling",
    ],
    primaryAction: "Open Compare",
  },
];

export default function ModeSelect() {
  const navigate = useNavigate();
  const { setMode } = useSession();

  const handleSelect = (modeKey, path) => {
    setMode(modeKey);
    navigate(path);
  };

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-10 text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 font-mono text-[11px] text-zinc-400 mb-3">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          RAG Development Environment
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-100 sm:text-4xl">
          Select Workspace Mode
        </h1>
        <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
          Choose an operational mode to begin. You can switch between active sessions from the top navigation at any time.
        </p>
      </div>

      {/* 3-Column Structured Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {modes.map((mode) => {
          const IconComponent = mode.icon;
          return (
            <div
              key={mode.key}
              onClick={() => handleSelect(mode.key, mode.path)}
              className="flex flex-col justify-between rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all cursor-pointer group"
            >
              <div>
                {/* Header row */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-800/80 border border-zinc-700/60 text-zinc-200 group-hover:text-amber-400 group-hover:border-zinc-600 transition-colors">
                    <IconComponent size={20} />
                  </div>
                  <Badge color={mode.badgeColor}>{mode.tag}</Badge>
                </div>

                {/* Title & Description */}
                <h2 className="text-lg font-semibold tracking-tight text-zinc-100 group-hover:text-white transition-colors">
                  {mode.label}
                </h2>
                <p className="mt-2 text-xs text-zinc-400 leading-relaxed min-h-[48px]">
                  {mode.description}
                </p>

                {/* Specs list */}
                <div className="mt-6 pt-5 border-t border-zinc-800/80 space-y-2">
                  <span className="font-mono text-[10px] text-zinc-500 uppercase tracking-wider block mb-2 font-medium">
                    Features & Capabilities
                  </span>
                  {mode.specs.map((spec) => (
                    <div key={spec} className="flex items-center gap-2 text-xs text-zinc-300">
                      <span className="w-1 h-1 rounded-full bg-zinc-600" />
                      <span>{spec}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Button */}
              <div className="mt-8 pt-4 border-t border-zinc-800/60 flex items-center justify-between">
                <span className="text-xs font-medium text-zinc-400 group-hover:text-zinc-200 transition-colors">
                  {mode.primaryAction}
                </span>
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-zinc-800 group-hover:bg-amber-500 group-hover:text-zinc-950 text-zinc-400 transition-all">
                  <IconArrowRight size={12} />
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* System info bar */}
      <div className="mt-12 rounded-lg border border-zinc-800/60 bg-zinc-900/20 px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs text-zinc-500 font-mono">
        <div className="flex items-center gap-4">
          <span>Engine: SQLite + ChromaDB</span>
          <span>·</span>
          <span>Vector Embeddings: NVIDIA / HuggingFace</span>
          <span>·</span>
          <span>LLM: Gemini / Groq</span>
        </div>
        <span className="text-emerald-400/80">● Local Database Connected</span>
      </div>
    </div>
  );
}
