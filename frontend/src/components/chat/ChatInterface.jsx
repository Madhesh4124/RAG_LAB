import { useState } from "react";
import MessageList from "./MessageList";
import InputBox from "./InputBox";
import { BASE_URL } from "../../services/api";

export default function ChatInterface({ docId, configId }) {
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
        body: JSON.stringify({ query, doc_id: docId, config_id: configId }),
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
      {/* Doc info bar */}
      {docId && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 mb-4 text-xs text-blue-700 flex justify-between items-center">
          <div>
            📄 Document: <span className="font-mono">{docId.slice(0, 8)}…</span>
            {configId && <> · Config: <span className="font-mono">{configId.slice(0, 8)}…</span></>}
          </div>
          <button 
             onClick={handleReset}
             className="text-red-500 hover:text-red-700 font-medium px-2 py-1 rounded hover:bg-red-50 transition-colors"
          >
            Reset System 🗑️
          </button>
        </div>
      )}

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