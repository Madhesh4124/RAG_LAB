import React, { useEffect, useMemo, useState } from "react";
import ChatInterface from "../components/chat/ChatInterface";
import { Button, Badge } from "../components/common/index";
import DocumentPicker from "../components/upload/DocumentPicker";
import UploadDocumentsModal from "../components/upload/UploadDocumentsModal";
import { useSession } from "../hooks/useSession";
import { applyBestPreset, getIndexStatus, prepareChatSession, uploadDocument } from "../services/api";
import { IconUpload, IconArrowRight, IconDocument, IconSettings } from "../components/common/Icons";

const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

export default function QuickChat() {
  const { docId, docIds, configId, setDocId, setDocIds, setConfigId, setFilename, setMode } = useSession();

  // Selected doc IDs sync with session
  const [selectedDocIds, setSelectedDocIds] = useState(() => {
    if (Array.isArray(docIds) && docIds.length) return docIds.map((id) => String(id));
    return docId ? [String(docId)] : [];
  });

  // Preserve chat stage if docId and configId already exist
  const [stage, setStage] = useState(() => (docId && configId ? "chat" : "ready"));
  const [showControls, setShowControls] = useState(() => !(docId && configId));

  const [isUploading,     setIsUploading]     = useState(false);
  const [uploadProgress,  setUploadProgress]  = useState(0);
  const [uploadFileIndex, setUploadFileIndex] = useState(0);
  const [uploadFileCount, setUploadFileCount] = useState(0);
  const [recentUploads,   setRecentUploads]   = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [error,           setError]           = useState("");
  const [reloadToken,     setReloadToken]     = useState(0);
  const [indexStatusMsg,  setIndexStatusMsg]  = useState("Preparing indexing job…");
  const [indexProgress,   setIndexProgress]   = useState(0);

  const primaryDocId = useMemo(() => selectedDocIds[0] || "", [selectedDocIds]);

  useEffect(() => { setMode("chat"); }, [setMode]);
  useEffect(() => { setDocIds(selectedDocIds); }, [selectedDocIds, setDocIds]);

  // If docId and configId exist in session on load or update, ensure stage is chat
  useEffect(() => {
    if (docId && configId && stage === "ready") {
      setStage("chat");
    }
  }, [docId, configId, stage]);

  const handleUpload = async (files) => {
    const nextFiles = Array.from(files || []).filter(Boolean);
    if (!nextFiles.length) return;
    setIsUploading(true); setUploadProgress(0); setUploadFileIndex(0);
    setUploadFileCount(nextFiles.length); setError("");
    try {
      const uploadedDocs = [], uploadedIds = [];
      for (let index = 0; index < nextFiles.length; index++) {
        const file = nextFiles[index];
        setUploadFileIndex(index + 1);
        const formData = new FormData();
        formData.append("file", file);
        const { data } = await uploadDocument(formData, (progress) => {
          const fp = Math.max(0, Math.min(100, Number(progress) || 0));
          setUploadProgress(Math.round(((index + fp / 100) / nextFiles.length) * 100));
        });
        uploadedDocs.push(data);
        const uid = data?.id;
        if (uid) uploadedIds.push(String(uid));
        setFilename(data?.filename || file.name);
      }
      if (uploadedDocs.length && uploadedIds.length) {
        const deduped = Array.from(new Set(uploadedIds));
        setSelectedDocIds(deduped);
        setDocId(deduped[0] || null);
        setConfigId(null);
        setStage("ready");
        setShowControls(true);
        setRecentUploads((prev) => [
          ...uploadedDocs.map((doc) => ({ id: doc?.id, filename: doc?.filename })),
          ...prev,
        ].slice(0, 5));
        setReloadToken((v) => v + 1);
        setShowUploadModal(false);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Upload failed");
    } finally { setIsUploading(false); }
  };

  const handleStartChat = async () => {
    if (!primaryDocId) return;

    // Fast-path: if this document was already prepared with this config, skip re-indexing!
    if (docId === primaryDocId && configId) {
      setStage("chat");
      setShowControls(false);
      return;
    }

    setStage("indexing");
    setError("");
    setIndexStatusMsg("Creating indexing job…");
    setIndexProgress(0);

    try {
      const { data } = await applyBestPreset({ document_id: primaryDocId });
      const nextConfigId = data?.id || null;
      if (!nextConfigId) throw new Error("Failed to configure pipeline.");

      setDocId(primaryDocId);
      setConfigId(nextConfigId);

      const prepareResponse = await prepareChatSession({
        document_id: primaryDocId,
        document_ids: selectedDocIds,
        config_id: nextConfigId,
      });

      const jobId = prepareResponse?.data?.job_id;
      if (jobId) {
        const startedAt = Date.now(), timeoutMs = 10 * 60 * 1000;
        while (true) {
          const statusResponse = await getIndexStatus(jobId);
          const status   = statusResponse?.data?.status   || "pending";
          const progress = Number(statusResponse?.data?.progress_pct ?? 0);
          setIndexProgress(progress);
          if (status === "ready")  { setIndexStatusMsg("Indexing complete."); setIndexProgress(100); break; }
          if (status === "failed") throw new Error(statusResponse?.data?.error || "Indexing failed.");
          setIndexStatusMsg(
            status === "indexing"
              ? `Processing ${selectedDocIds.length} document(s)… ${progress}%`
              : "Waiting for indexing engine…"
          );
          if ((Date.now() - startedAt) > timeoutMs) throw new Error("Indexing timed out.");
          await sleep(1000);
        }
      }
      setStage("chat");
      setShowControls(false);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to initialize pipeline");
      setStage("ready");
    } finally {
      setReloadToken((v) => v + 1);
    }
  };

  // ── Indexing screen ────────────────────────────────────────────────────────
  if (stage === "indexing") {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
        <div className="w-full rounded-xl border border-zinc-800 bg-zinc-900/60 p-8 text-center space-y-5">
          <div className="flex h-10 w-10 mx-auto items-center justify-center rounded-lg bg-zinc-800 border border-zinc-700 text-amber-500">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-700 border-t-amber-500" />
          </div>

          <div>
            <h1 className="text-base font-semibold text-zinc-100">Indexing Document Pipeline</h1>
            <p className="mt-1 text-xs text-zinc-400">
              Generating embeddings and building vector index for {selectedDocIds.length} document(s).
            </p>
          </div>

          <div className="space-y-2 text-left">
            <div className="flex justify-between text-[11px] font-mono text-zinc-400">
              <span>{indexStatusMsg}</span>
              <span className="text-amber-400 font-semibold">{indexProgress}%</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-amber-500 transition-all duration-300 ease-out"
                style={{ width: `${Math.max(5, indexProgress)}%` }}
              />
            </div>
          </div>

          <p className="text-[11px] text-zinc-500">
            High-dimension vector generation ensures fast, accurate retrieval during your session.
          </p>
        </div>
      </div>
    );
  }

  // ── Main Chat Layout ───────────────────────────────────────────────────────
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex flex-col gap-4 min-h-[calc(100vh-3.5rem)]">

      {/* Control / Document Selection Bar */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-300">
              <IconDocument size={16} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-zinc-100">Document Chat Workspace</h1>
                {docId && configId && (
                  <Badge color="emerald">Pipeline Ready</Badge>
                )}
              </div>
              <p className="text-xs text-zinc-400">
                {selectedDocIds.length > 0
                  ? `${selectedDocIds.length} document(s) active in session.`
                  : "Select or upload documents to start querying."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowUploadModal(true)}
              disabled={isUploading || stage === "indexing"}
              leadingIcon={<IconUpload size={12} />}
            >
              {isUploading ? `Uploading… ${uploadProgress}%` : "Upload Files"}
            </Button>
            {docId && configId ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowControls((v) => !v)}
              >
                {showControls ? "Hide Controls" : "Change Document"}
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={() => void handleStartChat()}
                disabled={!primaryDocId || isUploading || stage === "indexing"}
                trailingIcon={<IconArrowRight size={11} />}
              >
                Start Chat
              </Button>
            )}
          </div>
        </div>

        {/* Collapsible Document Selection panel */}
        {showControls && (
          <div className="mt-4 pt-4 border-t border-zinc-800/80 space-y-3">
            <DocumentPicker
              values={selectedDocIds}
              multiSelect
              reloadToken={reloadToken}
              onSelectMany={(docs) => {
                const ids = (docs || []).map((doc) => String(doc.id));
                // Only reset configId if selection actually changed to different docs!
                const isExactSame =
                  ids.length === selectedDocIds.length &&
                  ids.every((id, idx) => id === selectedDocIds[idx]);

                if (!isExactSame) {
                  setSelectedDocIds(ids);
                  setDocId(ids[0] || null);
                  setFilename(docs?.[0]?.filename || null);
                  setConfigId(null);
                  setStage("ready");
                }
              }}
              disabled={isUploading || stage === "indexing"}
              label="Select active documents for RAG context"
            />

            {selectedDocIds.length > 0 && (
              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-zinc-400 font-mono">
                  {selectedDocIds.length} file(s) selected
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedDocIds([]);
                    setDocId(null);
                    setFilename(null);
                    setConfigId(null);
                    setStage("ready");
                  }}
                  disabled={isUploading || stage === "indexing"}
                  className="text-xs text-zinc-500 hover:text-zinc-300 font-medium transition-colors cursor-pointer"
                >
                  Clear Selection
                </button>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="mt-3 rounded-lg border border-red-500/25 bg-red-500/10 p-3 text-xs text-red-300">
            {error}
          </div>
        )}
      </div>

      <UploadDocumentsModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleUpload}
        uploading={isUploading}
        progress={uploadProgress}
        allowMultiple
        title="Upload Documents to Workspace"
      />

      {/* Main Chat Interface Area */}
      <div className="flex-1 rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 flex flex-col min-h-[480px]">
        {docId && configId ? (
          <ChatInterface docId={docId} docIds={selectedDocIds} configId={configId} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-500 mb-3">
              <IconDocument size={22} />
            </div>
            <h3 className="text-sm font-semibold text-zinc-200">No Document Initialized</h3>
            <p className="mt-1 text-xs text-zinc-400 max-w-sm">
              Select an existing document above or upload a PDF/text file, then click <strong className="text-zinc-200">Start Chat</strong>.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
