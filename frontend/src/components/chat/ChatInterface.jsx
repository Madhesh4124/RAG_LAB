import React, { useEffect, useRef, useState } from 'react';
import MessageList from "./MessageList";
import InputBox from "./InputBox";
import { BASE_URL } from "../../services/api";
import EvaluationPanel from "../evaluation/EvaluationPanel";
import { getEvaluationReport } from "../../services/api";
import { IconChartLine, IconRefresh, IconSparkle } from "../common/Icons";

export default function ChatInterface({ docId, docIds = [], configId }) {
  const [messages,              setMessages]              = useState([]);
  const [loading,               setLoading]               = useState(false);
  const [showEvaluation,        setShowEvaluation]        = useState(false);
  const [selectedAssistantId,   setSelectedAssistantId]   = useState("");
  const [evaluationReport,      setEvaluationReport]      = useState(null);
  const [evaluationError,       setEvaluationError]       = useState("");
  const [deepEvaluationLoading, setDeepEvaluationLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    let cancelled = false;
    const hydrateHistory = async () => {
      if (!docId) { setMessages([]); return; }
      try {
        const response = await fetch(`${BASE_URL}/api/chat/history/${docId}`, {
          method: "GET", credentials: "include",
        });
        if (!response.ok) return;
        const rows = await response.json();
        if (cancelled || !Array.isArray(rows)) return;
        const filtered = configId
          ? rows.filter((item) => String(item.config_id) === String(configId))
          : rows;
        setMessages(filtered.map((item) => ({
          id: item.id, role: item.role, content: item.content || "",
          chunks: Array.isArray(item.retrieved_chunks) ? item.retrieved_chunks : [],
          timings: null, status: "",
        })));
      } catch (e) { console.error("Failed to restore history", e); }
    };
    void hydrateHistory();
    return () => { cancelled = true; };
  }, [docId, configId]);

  useEffect(() => {
    const assistantMessages = messages.filter((item) => item.role === "assistant" && item.id);
    if (!assistantMessages.length) { setSelectedAssistantId(""); return; }
    if (!selectedAssistantId || !assistantMessages.some((item) => String(item.id) === String(selectedAssistantId))) {
      setSelectedAssistantId(String(assistantMessages[assistantMessages.length - 1].id));
    }
  }, [messages, selectedAssistantId]);

  const handleSend = async (query) => {
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);
    let assistantMsg = { id: null, role: "assistant", content: "", chunks: [], timings: null, status: "" };
    let streamDone = false;
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const response = await fetch(`${BASE_URL}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ query, doc_id: docId, doc_ids: docIds, config_id: configId }),
      });
      if (!response.ok) throw new Error("Stream connection failed");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;
          try {
            const data = JSON.parse(trimmed.slice(5).trim());
            if (data.type === "status")   { assistantMsg = { ...assistantMsg, status: data.message }; }
            else if (data.type === "metadata") { assistantMsg = { ...assistantMsg, chunks: data.chunks, status: "" }; }
            else if (data.type === "token")    { assistantMsg = { ...assistantMsg, content: assistantMsg.content + data.content, status: "" }; }
            else if (data.type === "error") {
              assistantMsg = { ...assistantMsg, content: `${assistantMsg.content}\n\n[Error] ${data.message || "Unknown error"}`.trim(), status: "" };
              streamDone = true; setLoading(false);
            } else if (data.type === "done") {
              assistantMsg = { ...assistantMsg, id: data.message_id || assistantMsg.id, status: "" };
              streamDone = true; setLoading(false);
            }
            setMessages((prev) => { const next = [...prev]; next[next.length - 1] = { ...assistantMsg }; return next; });
            if (streamDone) { reader.cancel().catch(() => {}); break; }
          } catch (err) { console.error("JSON parse error in stream", err); }
        }
        if (streamDone) break;
      }
    } catch (e) {
      console.error(e);
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], content: `Error: ${e.message}`, status: "" };
        return next;
      });
    } finally { if (!streamDone) setLoading(false); }
  };

  const handleReset = async () => {
    if (!window.confirm("Clear all conversation history and vector indices for this session?")) return;
    try {
      setLoading(true);
      await fetch(`${BASE_URL}/api/chat/reset`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ doc_id: docId, config_id: configId }),
      });
      setMessages([]);
    } catch (e) { alert(`Reset failed: ${e.message}`); }
    finally { setLoading(false); }
  };

  const handleRunDeepEvaluation = async () => {
    if (!selectedAssistantId) return;
    setDeepEvaluationLoading(true); setEvaluationError("");
    try {
      const { data } = await getEvaluationReport({ message_id: selectedAssistantId, deep: true });
      setEvaluationReport(data);
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || "Evaluation failed.";
      setEvaluationError(String(detail).toLowerCase().includes("timeout")
        ? "Evaluation timed out. Please retry with a shorter prompt." : detail);
    } finally { setDeepEvaluationLoading(false); }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Top Toolbar */}
      <div className="flex items-center justify-end pb-3 mb-2 border-b border-zinc-800/80 flex-shrink-0 text-xs">
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setShowEvaluation(true); setEvaluationReport(null); setEvaluationError(""); }}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-zinc-800 bg-zinc-900 text-zinc-300 hover:bg-zinc-850 hover:text-white hover:border-zinc-700 transition-colors cursor-pointer text-xs font-medium"
          >
            <IconChartLine size={12} className="text-zinc-400" />
            <span>Evaluation</span>
          </button>
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-red-400 hover:border-red-500/30 hover:bg-red-500/10 transition-colors cursor-pointer text-xs font-medium"
          >
            <IconRefresh size={12} />
            <span>Reset History</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto pr-1 min-h-0">
        <MessageList messages={messages} />

        {loading && (
          <div className="flex items-center gap-2.5 py-2 text-xs text-zinc-400 font-mono">
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-zinc-700 border-t-amber-500" />
            <span>Synthesizing response with cited vectors…</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex-shrink-0 mt-3">
        <InputBox onSend={handleSend} loading={loading} />
      </div>

      {/* Evaluation Panel Modal */}
      <EvaluationPanel
        open={showEvaluation}
        onClose={() => setShowEvaluation(false)}
        title="Session Metrics & Evaluation"
        report={evaluationReport}
        loading={deepEvaluationLoading}
        error={evaluationError}
        onRunDeepEvaluation={handleRunDeepEvaluation}
        deepLoading={deepEvaluationLoading}
        selector={
          messages.filter((item) => item.role === "assistant" && item.id).length > 0 ? (
            <label className="block text-xs">
              <span className="mb-1 block font-mono text-[10px] text-zinc-400 uppercase tracking-wider">
                Select Assistant Turn
              </span>
              <select
                value={selectedAssistantId}
                onChange={(event) => { setEvaluationReport(null); setSelectedAssistantId(event.target.value); }}
                className="w-full rounded-md bg-zinc-900 border border-zinc-800 px-3 py-1.5 text-xs text-zinc-200 outline-none focus:border-amber-500/80 cursor-pointer"
              >
                {messages
                  .map((m, index) => ({ ...m, index }))
                  .filter((item) => item.role === "assistant" && item.id)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      Turn {item.index + 1}: {(item.content || "").slice(0, 70)}…
                    </option>
                  ))}
              </select>
            </label>
          ) : (
            <div className="rounded-md border border-dashed border-zinc-800 p-3 text-xs text-zinc-500">
              Generate at least one assistant answer to benchmark evaluation metrics.
            </div>
          )
        }
      />
    </div>
  );
}
