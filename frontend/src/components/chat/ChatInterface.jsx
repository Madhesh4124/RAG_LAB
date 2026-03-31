import { useState } from "react";
import MessageList from "./MessageList";
import InputBox from "./InputBox";
import { sendMessage } from "../../services/api";

export default function ChatInterface({ docId, configId }) {
  const [messages, setMessages] = useState([]);
  const [loading,  setLoading]  = useState(false);

  const handleSend = async (query) => {
    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);

    try {
      const { data } = await sendMessage({
        query,
        doc_id: docId,
        config_id: configId,
      });

      setMessages((prev) => [...prev, {
        role: "assistant",
        content: data.answer,
        chunks: data.retrieved_chunks,
        timings: data.timings,
      }]);
    } catch (e) {
      const errMsg = e.response?.data?.detail || e.message || "Chat request failed.";
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: `Chat failed: ${errMsg}`,
        chunks: [],
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Doc info bar */}
      {docId && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 mb-4 text-xs text-blue-700">
          📄 Document: <span className="font-mono">{docId.slice(0, 8)}…</span>
          {configId && <> · Config: <span className="font-mono">{configId.slice(0, 8)}…</span></>}
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