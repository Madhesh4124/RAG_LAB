import React from 'react';
import { useSearchParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useSession } from "../hooks/useSession";
import ChatInterface from "../components/chat/ChatInterface";
import { Button, Badge } from "../components/common/index";
import { getIndexStatus, prepareChatSession } from "../services/api";
import { IconArrowLeft, IconSettings, IconArrowUpRight, IconDocument } from "../components/common/Icons";

const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

export default function Chat() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [preparing, setPreparing] = useState(true);
  const [prepError, setPrepError] = useState("");
  const [prepStatus, setPrepStatus] = useState("Preparing chat session…");
  const [prepProgress, setPrepProgress] = useState(0);

  const docId = params.get("doc");
  const configId = params.get("config");
  const docsParam = params.get("docs");
  const { docIds: sessionDocIds } = useSession();

  const effectiveDocIds = (docsParam
    ? docsParam.split(",").filter(Boolean)
    : (sessionDocIds && sessionDocIds.length > 0 ? sessionDocIds : (docId ? [docId] : [])));

  useEffect(() => {
    let cancelled = false;

    const prepare = async () => {
      if (!docId || !configId) {
        setPreparing(false);
        setPrepError("Missing document or configuration ID.");
        return;
      }
      setPreparing(true);
      setPrepError("");
      setPrepStatus("Creating indexing job…");
      setPrepProgress(0);

      try {
        const { data } = await prepareChatSession({
          document_id: docId,
          document_ids: effectiveDocIds,
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
            if (status === "ready") { setPrepStatus("Indexing complete."); setPrepProgress(100); break; }
            if (status === "failed") throw new Error(statusResponse?.data?.error || "Indexing failed.");
            setPrepStatus(
              status === "indexing"
                ? `Indexing document… ${progress}%`
                : "Waiting for indexing engine…"
            );
            if ((Date.now() - startedAt) > timeoutMs)
              throw new Error("Indexing operation timed out. Please retry.");
            await sleep(1000);
          }
        }
      } catch (error) {
        if (!cancelled)
          setPrepError(error?.response?.data?.detail || error?.message || "Failed to prepare session.");
      } finally {
        if (!cancelled) setPreparing(false);
      }
    };
    void prepare();
    return () => { cancelled = true; };
  }, [docId, configId]);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex flex-col gap-4 min-h-[calc(100vh-3.5rem)]">
      {/* Top Header */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-300">
            <IconDocument size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-semibold text-zinc-100">Custom Pipeline Session</h1>
              <Badge color="blue">Custom Config</Badge>
            </div>
            <p className="text-xs text-zinc-400">
              Querying document using tailored chunking, embedding, and retrieval algorithms.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate(`/preview?doc=${docId}&config=${configId}`)}
            leadingIcon={<IconArrowLeft size={12} />}
          >
            Preview Chunks
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate("/setup")}
            leadingIcon={<IconSettings size={12} />}
          >
            Reconfigure
          </Button>
          <Button
            size="sm"
            onClick={() => navigate(`/compare?doc=${docId}`)}
            trailingIcon={<IconArrowUpRight size={11} />}
          >
            Compare
          </Button>
        </div>
      </div>

      {/* Error alert */}
      {prepError && (
        <div className="rounded-lg border border-red-500/25 bg-red-500/10 p-3 text-xs text-red-300">
          {prepError}
        </div>
      )}

      {/* Main Container */}
      <div className="flex-1 rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 flex flex-col min-h-[480px]">
        {preparing ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-sm mx-auto space-y-4">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-700 border-t-amber-500" />
            <div>
              <h3 className="text-sm font-semibold text-zinc-100">Preparing Pipeline Session</h3>
              <p className="mt-1 text-xs text-zinc-400">{prepStatus}</p>
            </div>
            <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-amber-500 transition-all duration-300 ease-out"
                style={{ width: `${Math.max(5, prepProgress)}%` }}
              />
            </div>
          </div>
        ) : (
          <ChatInterface docId={docId} docIds={effectiveDocIds} configId={configId} />
        )}
      </div>
    </div>
  );
}
