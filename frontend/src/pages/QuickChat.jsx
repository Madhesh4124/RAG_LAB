import React from 'react';
import { useEffect, useMemo, useState } from "react";

import ChatInterface from "../components/chat/ChatInterface";
import { Button } from "../components/common/index";
import DocumentPicker from "../components/upload/DocumentPicker";
import UploadDocumentsModal from "../components/upload/UploadDocumentsModal";
import { useSession } from "../hooks/useSession";
import { applyBestPreset, getIndexStatus, prepareChatSession, uploadDocument } from "../services/api";

const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

export default function QuickChat() {
  const { docId, docIds, configId, filename, setDocId, setDocIds, setConfigId, setFilename, setMode } = useSession();
  const [selectedDocIds, setSelectedDocIds] = useState(() => {
    if (Array.isArray(docIds) && docIds.length) return docIds.map((id) => String(id));
    return docId ? [String(docId)] : [];
  });
  const [stage, setStage] = useState("ready");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadFileIndex, setUploadFileIndex] = useState(0);
  const [uploadFileCount, setUploadFileCount] = useState(0);
  const [recentUploads, setRecentUploads] = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [indexStatusMessage, setIndexStatusMessage] = useState("Creating indexing job...");
  const [indexProgress, setIndexProgress] = useState(0);

  const primaryDocId = useMemo(() => selectedDocIds[0] || "", [selectedDocIds]);

  useEffect(() => {
    setMode("chat");
  }, []);

  useEffect(() => {
    setDocIds(selectedDocIds);
  }, [selectedDocIds, setDocIds]);

  const handleUpload = async (files) => {
    const nextFiles = Array.from(files || []).filter(Boolean);
    if (!nextFiles.length) return;

    setIsUploading(true);
    setUploadProgress(0);
    setUploadFileIndex(0);
    setUploadFileCount(nextFiles.length);
    setError("");

    try {
      const uploadedDocs = [];
      for (let index = 0; index < nextFiles.length; index += 1) {
        const file = nextFiles[index];
        setUploadFileIndex(index + 1);

        const formData = new FormData();
        formData.append("file", file);

        const { data } = await uploadDocument(formData, (progress) => {
          const fileProgress = Math.max(0, Math.min(100, Number(progress) || 0));
          const overallProgress = (((index + fileProgress / 100) / nextFiles.length) * 100);
          setUploadProgress(Math.round(overallProgress));
        });

        uploadedDocs.push(data);
        const uploadedId = data?.id;
        if (uploadedId) {
          setSelectedDocIds((prev) => {
            const next = [String(uploadedId), ...prev.filter((id) => String(id) !== String(uploadedId))];
            return Array.from(new Set(next));
          });
          setDocId(uploadedId);
        }
        setFilename(data?.filename || file.name);
        setConfigId(null);
      }

      if (uploadedDocs.length) {
        setRecentUploads((prev) => [...uploadedDocs.map((doc) => ({ id: doc?.id, filename: doc?.filename })), ...prev].slice(0, 5));
        setReloadToken((value) => value + 1);
        setShowUploadModal(false);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const handleStartChat = async () => {
    if (!primaryDocId) return;
    setStage("indexing");
    setError("");
    setIndexStatusMessage("Creating indexing job...");
    setIndexProgress(0);
    try {
      const { data } = await applyBestPreset({ document_id: primaryDocId });
      const nextConfigId = data?.id || null;
      if (!nextConfigId) {
        throw new Error("Failed to create chat configuration");
      }

      setDocId(primaryDocId);
      setConfigId(nextConfigId);
      const prepareResponse = await prepareChatSession({
        document_id: primaryDocId,
        document_ids: selectedDocIds,
        config_id: nextConfigId,
      });
      const jobId = prepareResponse?.data?.job_id;

      if (jobId) {
        const startedAt = Date.now();
        const timeoutMs = 10 * 60 * 1000;

        while (true) {
          const statusResponse = await getIndexStatus(jobId);
          const status = statusResponse?.data?.status || "pending";
          const progress = Number(statusResponse?.data?.progress_pct ?? 0);

          setIndexProgress(progress);

          if (status === "ready") {
            setIndexStatusMessage("Indexing complete.");
            setIndexProgress(100);
            break;
          }

          if (status === "failed") {
            throw new Error(statusResponse?.data?.error || "Indexing failed.");
          }

          setIndexStatusMessage(
            status === "indexing"
              ? `Indexing ${selectedDocIds.length} document(s)... ${progress}%`
              : "Waiting for indexing to start..."
          );

          if ((Date.now() - startedAt) > timeoutMs) {
            throw new Error("Indexing is taking too long. Please try again.");
          }

          await sleep(1000);
        }
      }
      setStage("chat");
      setShowControls(false);
    } catch (err) {
      setConfigId(null);
      setError(err?.response?.data?.detail || err?.message || "Failed to apply best preset");
      setStage("ready");
    } finally {
      setReloadToken((value) => value + 1);
    }
  };

  if (stage === "indexing") {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 flex flex-col h-[calc(100vh-80px)]">
        <div className="flex-1 grid place-items-center rounded-2xl border border-gray-200 bg-white px-6 py-10 shadow-sm text-center">
          <div className="space-y-4 max-w-md">
            <div className="mx-auto h-14 w-14 rounded-full border-4 border-blue-100 border-t-blue-600 animate-spin" />
            <h1 className="text-2xl font-bold text-gray-900">Indexing your document</h1>
            <p className="text-sm text-gray-500">
              We are preparing {selectedDocIds.length} selected document(s) before opening chat.
            </p>
            <div className="space-y-2">
              <p className="text-sm text-gray-600">{indexStatusMessage}</p>
              <div className="overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-2 rounded-full bg-blue-600 transition-all duration-300"
                  style={{ width: `${Math.max(8, indexProgress)}%` }}
                />
              </div>
              <p className="text-xs text-gray-400">{indexProgress}% complete</p>
            </div>
            <p className="text-xs text-gray-400">
              The first setup is doing the expensive pipeline work now so your chat starts faster.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 flex flex-col gap-4 h-[calc(100vh-80px)]">
      <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Chat</h1>
            {!showControls && docId && configId ? (
              <p className="text-sm text-gray-500 mt-1">{selectedDocIds.length} document(s) active</p>
            ) : (
              <>
                <p className="text-sm text-gray-500 mt-1">Choose a document and start chatting with the best preset automatically applied.</p>
                <p className="text-xs text-gray-400 mt-1">Pick multiple documents to chat across files. The first selected document will be the primary session anchor.</p>
              </>
            )}
          </div>
          {docId && configId && (
            <Button variant="secondary" onClick={() => setShowControls((value) => !value)}>
              {showControls ? "Hide Controls" : "Show Controls"}
            </Button>
          )}
        </div>

        {showControls && (
          <div className="mt-4 space-y-3">
            <DocumentPicker
              values={selectedDocIds}
              multiSelect
              reloadToken={reloadToken}
              onSelectMany={(docs) => {
                const ids = (docs || []).map((doc) => String(doc.id));
                setSelectedDocIds(ids);
                setDocId(ids[0] || null);
                setFilename(docs?.[0]?.filename || null);
                setConfigId(null);
              }}
              disabled={isUploading || stage === "indexing"}
              label="Select one or more previously uploaded documents"
            />

            <div className="grid gap-3 md:grid-cols-[auto_auto] justify-start">
            <Button variant="secondary" onClick={() => setShowUploadModal(true)} disabled={isUploading || stage === "indexing"}>
              {isUploading
                ? `Uploading ${uploadFileIndex}/${uploadFileCount} (${uploadProgress}%)`
                : "Upload Documents"}
            </Button>

            <Button onClick={() => void handleStartChat()} disabled={!primaryDocId || isUploading || stage === "indexing"}>
              {stage === "indexing" ? "Indexing..." : "Start Chat"}
            </Button>
            </div>

            {recentUploads.length > 0 && (
              <div className="text-xs text-gray-500 space-y-1">
                <p className="font-medium text-gray-600">Recently uploaded</p>
                <div className="flex flex-wrap gap-2">
                  {recentUploads.map((doc) => (
                    <span key={doc.id || doc.filename} className="rounded-full bg-gray-100 px-3 py-1">
                      {doc.filename}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      <UploadDocumentsModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleUpload}
        uploading={isUploading}
        progress={uploadProgress}
        allowMultiple
        title="Upload documents for Chat"
      />

      {docId && configId ? (
        <div className="flex-1 min-h-0">
          <ChatInterface docId={docId} docIds={selectedDocIds} configId={configId} />
        </div>
      ) : (
        <div className="flex-1 min-h-0 grid place-items-center text-sm text-gray-500 border border-dashed border-gray-300 rounded-2xl bg-white">
          Select or upload a document, then click Start Chat.
        </div>
      )}
    </div>
  );
}
