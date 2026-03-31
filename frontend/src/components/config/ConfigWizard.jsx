import { useConfig }    from "../../hooks/useConfig";
import { useDocument }  from "../../hooks/useDocument";
import { useSession }   from "../../hooks/useSession";
import DocumentUpload   from "../upload/DocumentUpload";
import PresetSelector   from "./PresetSelector";
import ChunkingStep     from "./ChunkingStep";
import { EmbeddingStep, VectorStoreStep, RetrievalStep } from "./Steps";
import { Button, StepIndicator } from "../common/index";
import { useNavigate } from "react-router-dom";
import { saveConfig } from "../../services/api";

const STEP_LABELS = ["Upload", "Chunking", "Embedding", "Vector Store", "Retrieval"];

export default function ConfigWizard() {
  const navigate = useNavigate();
  const { config, step, updateChunking, updateEmbedding, updateVectorstore, updateRetrieval, applyPreset, nextStep, prevStep } = useConfig();
  const { document, upload, uploading, uploadProgress, clearDocument } = useDocument();
  const { setDocId, setConfigId, setFilename } = useSession();

  const canAdvance = step === 0 ? !!document : true;
  const isLastStep = step === STEP_LABELS.length - 1;

  const handleComplete = async () => {
    if (!document?.id) return;
    try {
      const fullConfig = {
        chunker:     config.chunker,
        embedder:    config.embedder,
        vectorstore: config.vectorstore,
        retriever:   config.retriever,
        llm:         { provider: "gemini", model: "gemini-2.5-flash" },
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
    <DocumentUpload document={document} onUpload={upload} onClear={clearDocument} uploading={uploading} progress={uploadProgress} />,
    <ChunkingStep    config={config.chunker}      onChange={updateChunking} />,
    <EmbeddingStep   config={config.embedder}     onChange={updateEmbedding} />,
    <VectorStoreStep config={config.vectorstore}  onChange={updateVectorstore} />,
    <RetrievalStep   config={config.retriever}    onChange={updateRetrieval} />,
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