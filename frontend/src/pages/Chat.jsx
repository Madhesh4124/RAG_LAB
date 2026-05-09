import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from "react-router-dom";
import ChatInterface from "../components/chat/ChatInterface";
import { Button } from "../components/common/index";
import { getIndexStatus, prepareChatSession } from "../services/api";

const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

export default function Chat() {
  const [params]  = useSearchParams();
  const navigate  = useNavigate();
  const [preparing, setPreparing] = useState(true);
  const [prepError, setPrepError] = useState("");
  const [prepStatus, setPrepStatus] = useState("Preparing chat session...");
  const [prepProgress, setPrepProgress] = useState(0);

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
      setPrepStatus("Creating indexing job...");
      setPrepProgress(0);

      try {
        const { data } = await prepareChatSession({
          document_id: docId,
          document_ids: [docId],
          config_id: configId,
        });

        const jobId = data?.job_id;
        if (jobId) {
          const startedAt = Date.now();
          const timeoutMs = 10 * 60 * 1000;

          while (!cancelled) {
            const statusResponse = await getIndexStatus(jobId);
            const status = statusResponse?.data?.status || "pending";
            const progress = Number(statusResponse?.data?.progress_pct ?? 0);

            setPrepProgress(progress);

            if (status === "ready") {
              setPrepStatus("Indexing complete.");
              setPrepProgress(100);
              break;
            }

            if (status === "failed") {
              throw new Error(statusResponse?.data?.error || "Indexing failed.");
            }

            setPrepStatus(
              status === "indexing"
                ? `Indexing document... ${progress}%`
                : "Waiting for indexing to start..."
            );

            if ((Date.now() - startedAt) > timeoutMs) {
              throw new Error("Indexing is taking too long. Please try again.");
            }

            await sleep(1000);
          }
        }
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
        <div className="flex-1 grid place-items-center rounded-2xl border border-dashed border-gray-300 bg-white px-6 text-center">
          <div className="w-full max-w-md space-y-4">
            <div className="mx-auto h-12 w-12 rounded-full border-4 border-blue-100 border-t-blue-600 animate-spin" />
            <div>
              <p className="text-base font-semibold text-gray-900">Preparing chat session</p>
              <p className="mt-1 text-sm text-gray-500">{prepStatus}</p>
            </div>
            <div className="overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-2 rounded-full bg-blue-600 transition-all duration-300"
                style={{ width: `${Math.max(8, prepProgress)}%` }}
              />
            </div>
            <p className="text-xs text-gray-400">
              The first question will open only after indexing is actually ready.
            </p>
          </div>
        </div>
      ) : (
        <ChatInterface docId={docId} configId={configId} />
      )}
    </div>
  );
}
   
