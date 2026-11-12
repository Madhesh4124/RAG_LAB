import React, { useEffect, useMemo, useRef, useState } from 'react';
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
  IconRefresh,
} from "../common/Icons";

const STEP_LABELS = ["Upload Document", "Chunking Strategy", "Embeddings", "Retrieval & Rerank", "LLM & Memory"];

export default function ConfigWizard() {
  const navigate = useNavigate();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [pickerReloadToken, setPickerReloadToken] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const savingRef = useRef(false);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);
  const { config, step, updateChunking, updateEmbedding, updateRetrieval, updateLLM, updateMemory, applyPreset, nextStep, prevStep, goToStep, resetConfig } = useConfig();
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

    const handleReset = () => {
    resetConfig();
    handleClear();
  };

  const handleClear = () => {
    clearDocument();
    setDocId(null);
    setDocIds([]);
    setFilename(null);
  };

  const handleComplete = async () => {
    const targetDocId = selectedDocIds[0] || document?.id;
    if (!targetDocId || savingRef.current) return;
    savingRef.current = true;
    setSaving(true);
    setSaveError("");
    try {
      const fullConfig = {
        chunker:     config.chunker,
        embedder:    config.embedder,
        vectorstore: config.vectorstore,
        retriever:   config.retriever,
        reranker: {
          enabled:  config.retriever.reranker_enabled || false,
          provider: config.retriever.reranker_provider || "nvidia",
          model:    config.retriever.reranker_model    || "nvidia/nemotron-3.5-rerank-8b",
        },
        llm:    { ...config.llm },
        memory: config.memory.type === "none" ? {} : config.memory,
      };
      const { data } = await saveConfig({
        document_id: targetDocId,
        name: "Custom Pipeline",
        config_json: fullConfig,
      });
      if (!isMountedRef.current) return;
      setDocId(targetDocId);
      setConfigId(data.id);
      setFilename(filename || document?.filename || "Custom Pipeline");
      const docsParam = selectedDocIds.join(",");
      navigate(`/preview?doc=${targetDocId}&config=${data.id}&docs=${encodeURIComponent(docsParam)}`);
    } catch (e) {
      if (isMountedRef.current) {
        setSaveError(e.response?.data?.detail || e.message || "Failed to save pipeline configuration");
      }
    } finally {
      savingRef.current = false;
      if (isMountedRef.current) {
        setSaving(false);
      }
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
        <div className="flex flex-col sm:items-end gap-2.5">
          {step > 0 && <PresetSelector onSelect={applyPreset} />}
          {step > 0 && (
            <button
              type="button"
              onClick={handleReset}
              disabled={saving}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-zinc-700/80 bg-zinc-800/80 hover:bg-zinc-800 hover:border-zinc-600 text-zinc-300 hover:text-white text-xs font-semibold transition-all duration-200 cursor-pointer shadow-sm disabled:opacity-40"
              title="Reset pipeline and return to Step 1 (Upload Document)"
            >
              <IconRefresh size={12} className="text-amber-400" />
              <span>Reset to Step 1</span>
            </button>
          )}
        </div>
      </div>

      {/* Stepper bar */}
      <div className="py-1">
        <StepIndicator steps={STEP_LABELS} current={step} onStepClick={goToStep} />
      </div>

      {/* Active Step Panel */}
      <div className="min-h-[380px] rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
        {stepComponents[step]}
      </div>

      {saveError && (
        <div className="rounded-lg border border-red-500/25 bg-red-500/10 p-3 text-xs text-red-300">
          {saveError}
        </div>
      )}

      {/* Footer Navigation */}
      <div className="flex items-center justify-between pt-4 border-t border-zinc-800">
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={prevStep}
            disabled={step === 0 || saving}
            leadingIcon={<IconArrowLeft size={12} />}
          >
            Back
          </Button>
          {step > 0 && (
            <button
              type="button"
              onClick={handleReset}
              disabled={saving}
              className="inline-flex items-center gap-1 text-xs font-medium text-zinc-400 hover:text-amber-400 transition-colors cursor-pointer px-2 py-1 rounded hover:bg-white/[0.04] disabled:opacity-40"
              title="Return directly to Step 1 (Upload Document)"
            >
              <IconRefresh size={11} />
              <span>Reset to Step 1</span>
            </button>
          )}
        </div>

        <span className="font-mono text-[11px] text-zinc-500">
          Step {step + 1} of {STEP_LABELS.length}
        </span>

        {isLastStep ? (
          <Button
            size="sm"
            onClick={handleComplete}
            disabled={saving}
            trailingIcon={!saving ? <IconBuildPipeline size={12} /> : null}
          >
            {saving ? "Saving Pipeline…" : "Build & Preview Pipeline"}
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={nextStep}
            disabled={!canAdvance || saving}
            trailingIcon={<IconArrowRight size={12} />}
          >
            Next Step
          </Button>
        )}
      </div>
    </div>
  );
}