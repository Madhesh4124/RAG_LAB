import React, { useState, useMemo } from 'react';
import { useConfig }    from "../../hooks/useConfig";
import { useDocument }  from "../../hooks/useDocument";
import { useSession }   from "../../hooks/useSession";
import DocumentPicker   from "../upload/DocumentPicker";
import UploadDocumentsModal from "../upload/UploadDocumentsModal";
import PresetSelector   from "./PresetSelector";
import ChunkingStep     from "./ChunkingStep";
import { EmbeddingStep, RetrievalStep, LLMStep } from "./Steps";
import { Button, StepIndicator } from "../common/index";
import { useNavigate } from "react-router-dom";
import { saveConfig } from "../../services/api";
import {
  IconArrowLeft,
  IconArrowRight,
  IconBuildPipeline,
  IconUpload,
  IconSettings,
} from "../common/Icons";

const STEP_LABELS = ["Upload Document", "Chunking Strategy", "Embeddings", "Retrieval & Rerank", "LLM & Memory"];

export default function ConfigWizard() {
  const navigate = useNavigate();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [pickerReloadToken, setPickerReloadToken] = useState(0);
  const { config, step, updateChunking, updateEmbedding, updateRetrieval, updateLLM, updateMemory, applyPreset, nextStep, prevStep } = useConfig();
  const { document, upload, uploading, uploadProgress, clearDocument, selectDocument } = useDocument();
  const { docId, docIds, filename, setDocId, setDocIds, setConfigId, setFilename } = useSession();

  const selectedDocIds = useMemo(() => {
    if (docIds && docIds.length > 0) return docIds.map((id) => String(id));
    return docId ? [String(docId)] : [];
  }, [docIds, docId]);

  const canAdvance = step === 0 ? selectedDocIds.length > 0 || !!document : true;
  const isLastStep = step === STEP_LABELS.length - 1;

  const handleSelectManyDocuments = (docs) => {
    const ids = (docs || []).map((d) => String(d.id));
    setDocIds(ids);
    setDocId(ids[0] || null);
    const names = (docs || []).map((d) => d.filename).join(", ");
    setFilename(names || null);
    if (docs && docs[0]) {
      selectDocument({
        id: docs[0].id,
        filename: docs[0].filename,
        file_type: docs[0].file_type || "unknown",
        file_size: docs[0].file_size || 0,
        content: "",
      });
    } else {
      clearDocument();
    }
  };

  const handleClear = () => {
    clearDocument();
    setDocId(null);
    setDocIds([]);
    setFilename(null);
  };

  const handleComplete = async () => {
    const targetDocId = selectedDocIds[0] || document?.id;
    if (!targetDocId) return;
    try {
      const fullConfig = {
        chunker:     config.chunker,
        embedder:    config.embedder,
        vectorstore: config.vectorstore,
        retriever:   config.retriever,
        reranker: {
          enabled:  config.retriever.reranker_enabled || false,
          provider: config.retriever.reranker_provider || "huggingface_api",
          model:    config.retriever.reranker_model    || "BAAI/bge-reranker-base",
        },
        llm:    { ...config.llm },
        memory: config.memory.type === "none" ? {} : config.memory,
      };
      const { data } = await saveConfig({
        document_id: targetDocId,
        name: "Custom Pipeline",
        config_json: fullConfig,
      });
      setDocId(targetDocId);
      setConfigId(data.id);
      setFilename(filename || document?.filename || "Custom Pipeline");
      const docsParam = selectedDocIds.join(",");
      navigate(`/preview?doc=${targetDocId}&config=${data.id}&docs=${encodeURIComponent(docsParam)}`);
    } catch (e) {
      alert(`Failed: ${e.response?.data?.detail || e.message}`);
    }
  };

  const stepComponents = [
    /* Step 0: Upload */
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div>
          <h3 className="text-xs font-semibold text-zinc-100">Upload Source Documents</h3>
          <p className="text-[11px] text-zinc-400 mt-0.5">Upload PDF or TXT files to parse and tokenize into the pipeline.</p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowUploadModal(true)}
          disabled={uploading}
          leadingIcon={<IconUpload size={12} />}
        >
          {uploading ? `Uploading… ${uploadProgress}%` : "Upload Files"}
        </Button>
      </div>

      <DocumentPicker
        values={selectedDocIds}
        multiSelect
        onSelectMany={handleSelectManyDocuments}
        disabled={uploading}
        reloadToken={pickerReloadToken}
        label="Select Document(s) for Custom Pipeline"
      />

      {selectedDocIds.length > 0 && (
        <div className="flex items-center justify-between rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5">
          <div className="min-w-0 pr-3">
            <span className="font-mono text-[10px] text-amber-400 uppercase tracking-wider font-semibold">
              Selected Document{selectedDocIds.length > 1 ? `s (${selectedDocIds.length})` : ""}
            </span>
            <p className="text-xs font-semibold text-zinc-100 mt-0.5 truncate">
              {filename || document?.filename}
            </p>
          </div>
          <button
            onClick={handleClear}
            className="text-[11px] font-medium text-red-400 hover:text-red-300 bg-red-500/10 border border-red-500/20 px-2.5 py-1 rounded-md transition-colors cursor-pointer flex-shrink-0"
          >
            Clear Selection
          </button>
        </div>
      )}

      <UploadDocumentsModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={async (files) => {
          await upload(files);
          setPickerReloadToken((prev) => prev + 1);
        }}
        uploading={uploading}
        progress={uploadProgress}
        allowMultiple
        title="Upload Documents to Pipeline"
      />
    </div>,

    /* Steps 1–4 */
    <ChunkingStep  config={config.chunker}   onChange={updateChunking} />,
    <EmbeddingStep config={config.embedder}  onChange={updateEmbedding} />,
    <RetrievalStep config={config.retriever} onChange={updateRetrieval} />,
    <LLMStep
      config={config.llm}
      memoryConfig={config.memory}
      onLLMChange={updateLLM}
      onMemoryChange={updateMemory}
    />,
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-zinc-800">
        <div>
          <div className="flex items-center gap-2 font-mono text-[11px] text-zinc-500 mb-1">
            <IconSettings size={12} className="text-amber-500" />
            <span>Pipeline Architecture Studio</span>
          </div>
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">
            Configure RAG Pipeline
          </h1>
          <p className="text-zinc-400 text-xs mt-0.5">
            Step-by-step customization of chunking, vector embeddings, retrieval algorithms, and generation.
          </p>
        </div>
        {step > 0 && <PresetSelector onSelect={applyPreset} />}
      </div>

      {/* Stepper bar */}
      <div className="py-1">
        <StepIndicator steps={STEP_LABELS} current={step} />
      </div>

      {/* Active Step Panel */}
      <div className="min-h-[380px] rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
        {stepComponents[step]}
      </div>

      {/* Footer Navigation */}
      <div className="flex items-center justify-between pt-4 border-t border-zinc-800">
        <Button
          variant="secondary"
          size="sm"
          onClick={prevStep}
          disabled={step === 0}
          leadingIcon={<IconArrowLeft size={12} />}
        >
          Back
        </Button>

        <span className="font-mono text-[11px] text-zinc-500">
          Step {step + 1} of {STEP_LABELS.length}
        </span>

        {isLastStep ? (
          <Button
            size="sm"
            onClick={handleComplete}
            trailingIcon={<IconBuildPipeline size={12} />}
          >
            Build & Preview Pipeline
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={nextStep}
            disabled={!canAdvance}
            trailingIcon={<IconArrowRight size={12} />}
          >
            Next Step
          </Button>
        )}
      </div>
    </div>
  );
}