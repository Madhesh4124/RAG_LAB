import { useConfig }    from "../../hooks/useConfig";
import { useDocument }  from "../../hooks/useDocument";
import DocumentUpload   from "../upload/DocumentUpload";
import PresetSelector   from "./PresetSelector";
import ChunkingStep     from "./ChunkingStep";
import { EmbeddingStep, VectorStoreStep, RetrievalStep } from "./Steps";
import { Button, StepIndicator } from "../common/index";

const STEP_LABELS = ["Upload", "Chunking", "Embedding", "Vector Store", "Retrieval"];

export default function ConfigWizard({ onComplete }) {
  const {
    config, step, TOTAL_STEPS,
    updateChunking, updateEmbedding, updateVectorstore, updateRetrieval,
    applyPreset, nextStep, prevStep,
  } = useConfig();

  const { document, upload, uploading, uploadProgress, clearDocument } = useDocument();

  const canAdvance = step === 0 ? !!document : true;
  const isLastStep = step === STEP_LABELS.length - 1;

  const handleComplete = () => {
    // TODO: POST config to /api/config, then navigate to /chat or /preview
    console.log("Final config:", config, "doc:", document?.id);
    onComplete?.({ config, documentId: document?.id });
  };

  const stepComponents = [
    <DocumentUpload
      document={document}
      onUpload={upload}
      onClear={clearDocument}
      uploading={uploading}
      progress={uploadProgress}
    />,
    <ChunkingStep    config={config.chunking}     onChange={updateChunking} />,
    <EmbeddingStep   config={config.embedding}    onChange={updateEmbedding} />,
    <VectorStoreStep config={config.vectorstore}  onChange={updateVectorstore} />,
    <RetrievalStep   config={config.retrieval}    onChange={updateRetrieval} />,
  ];

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">

      {/* Header */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900">Configure RAG Pipeline</h1>
        <p className="text-gray-400 text-sm mt-1">Set each stage — or pick a preset to start fast.</p>
      </div>

      {/* Presets (hidden on upload step) */}
      {step > 0 && <PresetSelector onSelect={applyPreset} />}

      {/* Step indicator */}
      <div className="my-5">
        <StepIndicator steps={STEP_LABELS} current={step} />
      </div>

      {/* Step content */}
      <div className="min-h-[320px]">
        {stepComponents[step]}
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center mt-8 pt-4 border-t border-gray-100">
        <Button variant="secondary" onClick={prevStep} disabled={step === 0}>
          ← Back
        </Button>
        <span className="text-xs text-gray-300">Step {step + 1} / {STEP_LABELS.length}</span>
        {isLastStep
          ? <Button onClick={handleComplete}>Build Pipeline 🚀</Button>
          : <Button onClick={nextStep} disabled={!canAdvance}>Next →</Button>
        }
      </div>
    </div>
  );
}
