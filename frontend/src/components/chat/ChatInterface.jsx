import { useState } from "react";
import MessageList from "./MessageList";
import InputBox from "./InputBox";
import { sendMessage } from "../../services/api";

const MOCK_RESPONSE = {
  answer: "This document is a certificate from a government school confirming completion of an AICTE activity titled 'Helping Local Schools to Achieve Good Results'.",
  retrieved_chunks: [
    { id: "c1", text: "This is to certify that the undersigned student from the 8th semester...", score: 0.91 },
    { id: "c2", text: "This activity was conducted from 20-02-2026 to 27-02-2026 as part of the AICTE initiative.", score: 0.84 },
  ],
  timings: {
    chunking_time_ms: 120,
    embedding_time_ms: 340,
    retrieval_time_ms: 210,
    llm_time_ms: 1800,
    total_time_ms: 2470,
  },
  message_id: "mock-msg-1",
};

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
      // fallback to mock while backend is being fixed
      await new Promise((r) => setTimeout(r, 1500));
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: MOCK_RESPONSE.answer,
        chunks: MOCK_RESPONSE.retrieved_chunks,
        timings: MOCK_RESPONSE.timings,
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