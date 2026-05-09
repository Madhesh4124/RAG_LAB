import React from 'react';
import { useEffect, useState } from "react";
import MessageList from "./MessageList";
import InputBox from "./InputBox";
import { BASE_URL } from "../../services/api";
import EvaluationPanel from "../evaluation/EvaluationPanel";
import { getEvaluationReport } from "../../services/api";

export default function ChatInterface({ docId, docIds = [], configId }) {
  const [messages, setMessages] = useState([]);
  const [loading,  setLoading]  = useState(false);
  const [showEvaluation, setShowEvaluation] = useState(false);
  const [selectedAssistantId, setSelectedAssistantId] = useState("");
  const [evaluationReport, setEvaluationReport] = useState(null);
  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [evaluationError, setEvaluationError] = useState("");
  const [deepEvaluationLoading, setDeepEvaluationLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const hydrateHistory = async () => {
      if (!docId) {
        setMessages([]);
        return;
      }

      try {
        const response = await fetch(`${BASE_URL}/api/chat/history/${docId}`, {
          method: "GET",
          credentials: "include",
        });
        if (!response.ok) return;

        const rows = await response.json();
        if (cancelled || !Array.isArray(rows)) return;

        const filtered = configId
          ? rows.filter((item) => String(item.config_id) === String(configId))
          : rows;

        const hydrated = filtered.map((item) => ({
          id: item.id,
          role: item.role,
          content: item.content || "",
          chunks: Array.isArray(item.retrieved_chunks) ? item.retrieved_chunks : [],
          timings: null,
          status: "",
        }));

        setMessages(hydrated);
      } catch (e) {
        console.error("Failed to restore chat history", e);
      }
    };

    void hydrateHistory();
    return () => {
      cancelled = true;
    };
  }, [docId, configId]);

  useEffect(() => {
    const assistantMessages = messages.filter((item) => item.role === "assistant" && item.id);
    if (!assistantMessages.length) {
      setSelectedAssistantId("");
      return;
    }

    if (!selectedAssistantId || !assistantMessages.some((item) => String(item.id) === String(selectedAssistantId))) {
      setSelectedAssistantId(String(assistantMessages[assistantMessages.length - 1].id));
    }
  }, [messages, selectedAssistantId]);

  useEffect(() => {
    if (!showEvaluation || !selectedAssistantId) return;

    let cancelled = false;
    const loadReport = async () => {
      setEvaluationLoading(true);
      setEvaluationError("");
      try {
        const { data } = await getEvaluationReport({ message_id: selectedAssistantId, deep: false });
        if (!cancelled) {
          setEvaluationReport(data);
        }
      } catch (error) {
        if (!cancelled) {
          setEvaluationError(error?.response?.data?.detail || error?.message || "Failed to load evaluation report.");
          setEvaluationReport(null);
        }
      } finally {
        if (!cancelled) {
          setEvaluationLoading(false);
        }
      }
    };

    void loadReport();
    return () => {
      cancelled = true;
    };
  }, [showEvaluation, selectedAssistantId]);

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
            if (data.type === "status") {
              assistantMsg = { ...assistantMsg, status: data.message };
            } else if (data.type === "metadata") {
              assistantMsg = { ...assistantMsg, chunks: data.chunks, status: "" };
            } else if (data.type === "token") {
              assistantMsg = { ...assistantMsg, content: assistantMsg.content + data.content, status: "" };
            } else if (data.type === "error") {
              const details = data.message || "Unknown stream error";
              assistantMsg = {
                ...assistantMsg,
                content: `${assistantMsg.content}\n\n[Stream error] ${details}`.trim(),
                status: "",
              };
              streamDone = true;
              setLoading(false);
            } else if (data.type === "done") {
              assistantMsg = { ...assistantMsg, id: data.message_id || assistantMsg.id, status: "" };
              streamDone = true;
              setLoading(false);
            }
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...assistantMsg };
              return next;
            });

            if (streamDone) {
              reader.cancel().catch(() => {});
              break;
            }
          } catch (err) {
            console.error("JSON parse error in stream", err);
          }
        }

        if (streamDone) {
          break;
        }
      }

      if (!streamDone && buffer.trim()) {
        const finalLine = buffer.trim();
        if (finalLine.startsWith("data:")) {
          try {
            const data = JSON.parse(finalLine.slice(5).trim());
            if (data.type === "done") {
              assistantMsg = { ...assistantMsg, id: data.message_id || assistantMsg.id, status: "" };
              setMessages((prev) => {
                const next = [...prev];
                next[next.length - 1] = { ...assistantMsg };
                return next;
              });
            } else if (data.type === "error") {
              const details = data.message || "Unknown stream error";
              setMessages((prev) => {
                const next = [...prev];
                next[next.length - 1] = {
                  ...next[next.length - 1],
                  content: `${next[next.length - 1].content}\n\n[Stream error] ${details}`.trim(),
                  status: "",
                };
                return next;
              });
            }
          } catch (err) {
            console.error("JSON parse error in final stream buffer", err);
          }
        }
      }
    } catch (e) {
      console.error(e);
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], content: `Error: ${e.message}`, status: "" };
        return next;
      });
    } finally {
      if (!streamDone) {
        setLoading(false);
      }
    }
  };

  const handleReset = async () => {
    if (!window.confirm("This will clear ALL conversation history and vectordb indices. Continue?")) return;
    try {
      setLoading(true);
      await fetch(`${BASE_URL}/api/chat/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ doc_id: docId, config_id: configId }),
      });
      setMessages([]);
      alert("System Reset Complete.");
    } catch (e) {
      alert(`Reset failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRunDeepEvaluation = async () => {
    if (!selectedAssistantId) return;
    setDeepEvaluationLoading(true);
    setEvaluationError("");
    try {
      const { data } = await getEvaluationReport({ message_id: selectedAssistantId, deep: true });
      setEvaluationReport(data);
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || "Failed to run deep evaluation.";
      if (String(detail).toLowerCase().includes("timeout")) {
        setEvaluationError("Deep evaluation took too long and was stopped. Use the fast report or retry later.");
      } else {
        setEvaluationError(detail);
      }
    } finally {
      setDeepEvaluationLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="mb-2 flex justify-end gap-2">
        <button
          onClick={() => {
            setShowEvaluation(true);
            setEvaluationReport(null);
            setEvaluationError("");
          }}
          className="text-xs text-gray-400 hover:text-blue-600 px-2 py-1 rounded hover:bg-gray-100 transition-colors"
          title="Open evaluation panel"
        >
          Evaluation
        </button>
        <button
          onClick={handleReset}
          className="text-xs text-gray-400 hover:text-red-600 px-2 py-1 rounded hover:bg-gray-100 transition-colors"
          title="Reset session"
        >
          Reset
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto pr-1">
        <MessageList messages={messages} />
        {loading && (
          <div className="flex justify-start mt-4">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1 items-center">
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <InputBox onSend={handleSend} loading={loading} />

      <EvaluationPanel
        open={showEvaluation}
        onClose={() => setShowEvaluation(false)}
        title="Chat Evaluation"
        report={evaluationReport}
        loading={evaluationLoading}
        error={evaluationError}
        onRunDeepEvaluation={handleRunDeepEvaluation}
        deepLoading={deepEvaluationLoading}
        selector={messages.filter((item) => item.role === "assistant" && item.id).length > 0 ? (
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-gray-500">Assistant turn</span>
            <select
              value={selectedAssistantId}
              onChange={(event) => {
                setEvaluationReport(null);
                setSelectedAssistantId(event.target.value);
              }}
              className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
            >
              {messages
                .map((message, index) => ({ ...message, index }))
                .filter((item) => item.role === "assistant" && item.id)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    Turn {item.index + 1}: {(item.content || "").slice(0, 72) || "Assistant response"}
                  </option>
                ))}
            </select>
          </label>
        ) : (
          <div className="rounded-xl border border-dashed border-gray-200 px-3 py-3 text-sm text-gray-400">
            Ask at least one question to generate evaluation metrics.
          </div>
        )}
      />
    </div>
  );
}
