import React from 'react';
import { useNavigate } from "react-router-dom";

import { useSession } from "../hooks/useSession";

export default function ModeSelect() {
  const navigate = useNavigate();
  const { setMode } = useSession();

  const selectMode = (mode, path) => {
    setMode(mode);
    navigate(path);
  };

  return (
    <div className="min-h-[calc(100vh-64px)] bg-gray-50 p-6">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-2xl font-bold text-gray-900">Choose Mode</h1>
        <p className="text-sm text-gray-500 mt-1">Pick how you want to work in this session.</p>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <button
            onClick={() => selectMode("chat", "/chat")}
            className="text-left rounded-2xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300"
            aria-label="Chat mode"
          >
            <h2 className="font-semibold text-gray-900">Chat</h2>
            <p className="text-sm text-gray-500 mt-2">Upload/select a document and start chatting with best preset defaults.</p>
          </button>

          <button
            onClick={() => selectMode("custom-chat", "/setup")}
            className="text-left rounded-2xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300"
            aria-label="Custom Chat mode"
          >
            <h2 className="font-semibold text-gray-900">Custom Chat</h2>
            <p className="text-sm text-gray-500 mt-2">Configure chunking, embedding, retrieval, and chat behavior.</p>
          </button>

          <button
            onClick={() => selectMode("compare", "/compare")}
            className="text-left rounded-2xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300"
            aria-label="Compare Chat mode"
          >
            <h2 className="font-semibold text-gray-900">Compare Chat</h2>
            <p className="text-sm text-gray-500 mt-2">Run and compare multiple RAG configurations side by side.</p>
          </button>
        </div>
      </div>
    </div>
  );
}
