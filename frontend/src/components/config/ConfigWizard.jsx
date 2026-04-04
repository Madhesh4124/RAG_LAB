import React from 'react';
import { useState } from "react";
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

const STEP_LABELS = ["Upload", "Chunking", "Embedding", "Retrieval", "LLM & Memory"];

export default function ConfigWizard() {
  const navigate = useNavigate();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const { config, step, updateChunking, updateEmbedding, updateRetrieval, updateLLM, updateMemory, applyPreset, nextStep, prevStep } = useConfig();
  const { document, upload, uploading, uploadProgress, clearDocument, selectDocument } = useDocument();
  const { setDocId, setConfigId, setFilename } = useSession();

  const canAdvance = step === 0 ? !!document : true;
  const isLastStep = step === STEP_LABELS.length - 1;

  const handleSelectExistingDocument = (doc) => {
    if (!doc) return;
    selectDocument({
      id: doc.id,
      filename: doc.filename,
      file_type: doc.file_type || "unknown",
      file_size: doc.file_size || 0,
      content: "",
    });
    setDocId(doc.id);
    setFilename(doc.filename);
  };

  const handleComplete = async () => {
    if (!document?.id) return;
    try {
      const fullConfig = {
        chunker:     config.chunker,
        embedder:    config.embedder,
        vectorstore: config.vectorstore,
        retriever:   config.retriever,
        reranker:    {
          enabled: config.retriever.reranker_enabled || false,
          provider: config.retriever.reranker_provider || "huggingface_api",
          model: config.retriever.reranker_model || "BAAI/bge-reranker-base",
        },
        llm:         { ...config.llm },
        memory:      config.memory.type === "none" ? {} : config.memory,
      };
      const { data } = await saveConfig({
        document_id: document.id,
        name: "My Config",
        config_json: fullConfig,
      });
      setDocId(document.id);
      setConfigId(data.id);
      setFilename(document.filename);
      navigate(`/preview?doc=${document.id}&config=${data.id}`);
    } catch (e) {
      alert(`Failed: ${e.response?.data?.detail || e.message}`);
    }
  };

  const stepComponents = [
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-3">
        <p className="text-sm text-gray-600">Upload document(s) through a compact dialog.</p>
        <Button variant="secondary" onClick={() => setShowUploadModal(true)} disabled={uploading}>
          {uploading ? `Uploading... ${uploadProgress}%` : "Upload Documents"}
        </Button>
      </div>
      <DocumentPicker value={document?.id || ""} onSelect={handleSelectExistingDocument} disabled={uploading} />
      {document && (
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
          <p className="text-sm text-gray-700">Selected: <span className="font-medium">{document.filename}</span></p>
          <button onClick={clearDocument} className="mt-2 text-xs text-blue-600 hover:text-blue-700">Clear selection</button>
        </div>
      )}
      <UploadDocumentsModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={upload}
        uploading={uploading}
        progress={uploadProgress}
        allowMultiple
        title="Upload documents for Custom Chat"
      />
    </div>,
    <ChunkingStep    config={config.chunker}      onChange={updateChunking} />,
    <EmbeddingStep   config={config.embedder}     onChange={updateEmbedding} />,
    <RetrievalStep   config={config.retriever}    onChange={updateRetrieval} />,
    <LLMStep         config={config.llm}          memoryConfig={config.memory} onLLMChange={updateLLM} onMemoryChange={updateMemory} />,
  ];

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900">Configure RAG Pipeline</h1>
        <p className="text-gray-400 text-sm mt-1">Set each stage — or pick a preset to start fast.</p>
      </div>

      {step > 0 && <PresetSelector onSelect={applyPreset} />}

      <div className="my-5">
        <StepIndicator steps={STEP_LABELS} current={step} />
      </div>

      <div className="min-h-[320px]">
        {stepComponents[step]}
      </div>

      <div className="flex justify-between items-center mt-8 pt-4 border-t border-gray-100">
        <Button variant="secondary" onClick={prevStep} disabled={step === 0}>← Back</Button>
        <span className="text-xs text-gray-300">Step {step + 1} / {STEP_LABELS.length}</span>
        {isLastStep
          ? <Button onClick={handleComplete}>Build Pipeline 🚀</Button>
          : <Button onClick={nextStep} disabled={!canAdvance}>Next →</Button>
        }
      </div>
    </div>
  );
}