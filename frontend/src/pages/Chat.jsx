import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from "react-router-dom";
import ChatInterface from "../components/chat/ChatInterface";
import { Button } from "../components/common/index";
import { prepareChatSession } from "../services/api";

export default function Chat() {
  const [params]  = useSearchParams();
  const navigate  = useNavigate();
  const [preparing, setPreparing] = useState(true);
  const [prepError, setPrepError] = useState("");

  const docId     = params.get("doc");
  const configId  = params.get("config");

  useEffect(() => {
    let cancelled = false;

    const prepare = async () => {
      if (!docId || !configId) {
        setPreparing(false);
        setPrepError("Missing document or configuration.");
        return;
      }

      setPreparing(true);
      setPrepError("");

      try {
        await prepareChatSession({
          document_id: docId,
          document_ids: [docId],
          config_id: configId,
        });
      } catch (error) {
        if (!cancelled) {
          setPrepError(error?.response?.data?.detail || error?.message || "Failed to prepare chat session.");
        }
      } finally {
        if (!cancelled) {
          setPreparing(false);
        }
      }
    };

    void prepare();

    return () => {
      cancelled = true;
    };
  }, [docId, configId]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Custom Chat</h1>
          <p className="text-sm text-gray-400 mt-1">Ask questions with your selected custom configuration.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate(`/preview?doc=${docId}&config=${configId}`)}>
            ← Chunk Preview
          </Button>
          <Button variant="secondary" onClick={() => navigate("/setup")}>
            Reconfigure
          </Button>
          <Button onClick={() => navigate(`/compare?doc=${docId}`)}>
            Compare Mode →
          </Button>
        </div>
      </div>
      {prepError && (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {prepError}
        </div>
      )}
      {preparing ? (
        <div className="flex-1 grid place-items-center rounded-2xl border border-dashed border-gray-300 bg-white text-sm text-gray-500">
          Preparing chat session...
        </div>
      ) : (
        <ChatInterface docId={docId} configId={configId} />
      )}
    </div>
  );
}
   