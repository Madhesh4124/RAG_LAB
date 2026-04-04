import React from 'react';
import { useState } from "react";
import MessageList from "./MessageList";
import InputBox from "./InputBox";
import { BASE_URL } from "../../services/api";

export default function ChatInterface({ docId, docIds = [], configId }) {
  const [messages, setMessages] = useState([]);
  const [loading,  setLoading]  = useState(false);

  const handleSend = async (query) => {
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);

    let assistantMsg = { role: "assistant", content: "", chunks: [], timings: null, status: "" };
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
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "status") {
              assistantMsg = { ...assistantMsg, status: data.message };
            } else if (data.type === "metadata") {
              assistantMsg = { ...assistantMsg, chunks: data.chunks, status: "" };
            } else if (data.type === "token") {
              assistantMsg = { ...assistantMsg, content: assistantMsg.content + data.content, status: "" };
            } else if (data.type === "done") {
              assistantMsg = { ...assistantMsg, status: "" };
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
        if (finalLine.startsWith("data: ")) {
          try {
            const data = JSON.parse(finalLine.slice(6));
            if (data.type === "done") {
              assistantMsg = { ...assistantMsg, status: "" };
              setMessages((prev) => {
                const next = [...prev];
                next[next.length - 1] = { ...assistantMsg };
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

  return (
    <div className="flex flex-col h-full">
      <div className="mb-2 flex justify-end">
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
    </div>
  );
}