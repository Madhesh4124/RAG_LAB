import React from 'react';
import { useEffect, useMemo, useRef, useState } from "react";
import { clearChromaDb, compareConfigs, compareIndex, uploadDocument } from "../services/api";
import { useSession } from "../hooks/useSession";
import { Button } from "../components/common/index";
import DatasetBanner from "../components/compare/DatasetBanner";
import ConfigCard from "../components/compare/ConfigCard";
import ConfigFormModal from "../components/compare/ConfigFormModal";
import StagingPanel from "../components/compare/StagingPanel";
import QueryInput from "../components/compare/QueryInput";
import ResultsGrid from "../components/compare/ResultsGrid";
import DocumentPicker from "../components/upload/DocumentPicker";
import UploadDocumentsModal from "../components/upload/UploadDocumentsModal";

const MAX_CONFIGS = 4;

function deriveCollectionName(embeddingProvider, embeddingModel, chunkStrategy) {
  const normalizedModel = String(embeddingModel || "")
    .toLowerCase()
    .replace(/[\/\-.\s]+/g, "_");
  return `${embeddingProvider}_${normalizedModel}_${chunkStrategy}`.toLowerCase();
}

function createPresetConfigs() {
  return [
    {
      name: "Broad Recall",
      chunk_strategy: "fixed_size",
      chunk_params: { chunk_size: 512, overlap: 50 },
      embedding_provider: "nvidia",
      embedding_model: "nvidia/nemotron-3-embed-1b",
      top_k: 8,
      threshold: 0.3,
    },
    {
      name: "Precision Focus",
      chunk_strategy: "semantic",
      chunk_params: {
        max_chunk_size: 512,
        min_chunk_size: 100,
        similarity_threshold: 0.7,
        hard_split_threshold: 0.4,
        overlap_sentences: 1,
      },
      embedding_provider: "huggingface",
      embedding_model: "sentence-transformers/all-MiniLM-L6-v2",
      top_k: 3,
      threshold: 0.7,
    },
  ].map((config) => ({
    ...config,
    collection_name: deriveCollectionName(
      config.embedding_provider,
      config.embedding_model,
      config.chunk_strategy,
    ),
    indexingStatus: "idle",
    isPreset: true,
  }));
}

export default function ComparePage() {
  const {
    docId: activeDocId,
    docIds,
    filename: activeDataset,
    setDocId,
    setDocIds,
    setFilename,
    stagedConfigs,
    setStagedConfigs,
    isQueryUnlocked,
    setIsQueryUnlocked,
  } = useSession();
  const [availableConfigs, setAvailableConfigs] = useState(createPresetConfigs);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunningStaged, setIsRunningStaged] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [toast, setToast] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const resultsRef = useRef(null);
  const activeDatasetRef = useRef(activeDataset);

  const isDatasetMissing = !activeDataset || !activeDocId;
  const stagedLookup = useMemo(() => new Set(stagedConfigs.map((config) => config.name)), [stagedConfigs]);
  const getConfigByName = (name) => availableConfigs.find((config) => config.name === name);
  const stagedConfigsLive = useMemo(
    () => stagedConfigs.map((config) => getConfigByName(config.name) || config),
    [stagedConfigs, availableConfigs],
  );
  const readyStatuses = new Set(["ready", "already_exists"]);
  const hasPendingIndexing = stagedConfigs.some((config) => {
    const current = getConfigByName(config.name);
    return !current || !readyStatuses.has(current.indexingStatus);
  });
  const isUiBlocked = isDatasetMissing || isLoading || hasPendingIndexing || !isQueryUnlocked;

  useEffect(() => {
    if (!results || !results.length) return;
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [results]);

  // Only reset staged configs if the dataset actually changes to a DIFFERENT file
  useEffect(() => {
    if (activeDatasetRef.current !== activeDataset) {
      activeDatasetRef.current = activeDataset;
      setAvailableConfigs(createPresetConfigs());
      setStagedConfigs([]);
      setResults(null);
      setQuery("");
      setIsQueryUnlocked(false);
      setShowConfigModal(false);
    }
  }, [activeDataset, setStagedConfigs, setIsQueryUnlocked]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const showToast = (message, type = "success") => {
    setToast({ message, type });
  };

  const updateConfigByName = (name, patch) => {
    setAvailableConfigs((prev) => prev.map((config) => (config.name === name ? { ...config, ...patch } : config)));
  };

  const indexConfig = async (config) => {
    const datasetSnapshot = activeDatasetRef.current;
    updateConfigByName(config.name, { indexingStatus: "indexing" });
    try {
      const effectiveDocIds = docIds && docIds.length > 0 ? docIds : (activeDocId ? [activeDocId] : []);
      const { data } = await compareIndex({
        document_id: activeDocId,
        document_ids: effectiveDocIds,
        config: {
          name: config.name,
          chunk_strategy: config.chunk_strategy,
          chunk_params: config.chunk_params || {},
          embedding_provider: config.embedding_provider,
          embedding_model: config.embedding_model,
          top_k: Number(config.top_k),
          threshold: Number(config.threshold),
        },
      });

      if (activeDatasetRef.current !== datasetSnapshot) return;

      const status = data?.status === "already_exists" ? "already_exists" : "ready";
      updateConfigByName(config.name, {
        indexingStatus: status,
        collection_name: data?.collection_name || config.collection_name,
      });
      showToast(status === "already_exists" ? `"${config.name}" already indexed.` : `"${config.name}" is ready.`);
      return status;
    } catch (error) {
      if (activeDatasetRef.current !== datasetSnapshot) return;
      updateConfigByName(config.name, { indexingStatus: "error" });
      showToast(error?.response?.data?.detail || error?.message || `Failed to index "${config.name}".`, "error");
      return "error";
    }
  };

  const handleAddConfig = (config) => {
    const current = getConfigByName(config.name);
    if (!current) {
      showToast(`"${config.name}" is unavailable.`, "warning");
      return;
    }
    if (stagedLookup.has(config.name)) {
      showToast(`"${config.name}" is already staged.`, "warning");
      return;
    }
    if (stagedConfigs.length >= MAX_CONFIGS) {
      showToast("You can stage up to 4 configs only.", "warning");
      return;
    }

    setStagedConfigs((prev) => [...prev, current]);
    setIsQueryUnlocked(false);
    showToast(`Added "${config.name}" to staging.`);
  };

  const handleRemoveConfig = (name) => {
    setStagedConfigs((prev) => prev.filter((config) => config.name !== name));
    setIsQueryUnlocked(false);
    showToast(`Removed "${name}" from staging.`);
  };

  const handleClearAll = () => {
    setStagedConfigs([]);
    setIsQueryUnlocked(false);
    showToast("Cleared all staged configs.");
  };

  const handleSaveCustomConfig = (config) => {
    const nextConfig = {
      ...config,
      collection_name: deriveCollectionName(
        config.embedding_provider,
        config.embedding_model,
        config.chunk_strategy,
      ),
      indexingStatus: "idle",
      isPreset: false,
    };

    setAvailableConfigs((prev) => [...prev, nextConfig]);
    setShowConfigModal(false);
    setIsQueryUnlocked(false);
    showToast(`Saved "${config.name}". Add it to staging and run to save configs.`);
  };

  const handleUpload = async (files) => {
    const nextFiles = Array.from(files || []).filter(Boolean);
    if (!nextFiles.length) return;

    setIsUploading(true);
    setUploadProgress(0);
    try {
      let lastUploaded = null;
      const uploadedIds = [];
      const uploadedNames = [];
      for (let index = 0; index < nextFiles.length; index += 1) {
        const file = nextFiles[index];
        const formData = new FormData();
        formData.append("file", file);
        const { data } = await uploadDocument(formData, (progress) => {
          const current = Math.max(0, Math.min(100, Number(progress) || 0));
          const overall = ((index + current / 100) / nextFiles.length) * 100;
          setUploadProgress(Math.round(overall));
        });
        lastUploaded = data;
        if (data?.id) {
          uploadedIds.push(String(data.id));
          uploadedNames.push(data.filename || file.name);
        }
      }
      if (lastUploaded) {
        setDocId(lastUploaded?.id || null);
        if (uploadedIds.length > 0) {
          setDocIds(uploadedIds);
          setFilename(uploadedNames.join(", "));
        } else {
          setFilename(lastUploaded?.filename || nextFiles[nextFiles.length - 1].name);
        }
      }
      showToast(`Uploaded ${nextFiles.length} file(s).`);
      setShowUploadModal(false);
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || "Upload failed.";
      showToast(detail, "error");
    } finally {
      setIsUploading(false);
    }
  };

  const handleClearChromaDb = async () => {
    const confirmed = window.confirm("This will delete all ChromaDB collections and indexes in this app. Continue?");
    if (!confirmed) return;

    try {
      setIsLoading(true);
      setIsRunningStaged(false);
      setIsQueryUnlocked(false);
      setResults(null);
      setQuery("");
      setStagedConfigs([]);
      const { data } = await clearChromaDb();
      setAvailableConfigs(createPresetConfigs());
      showToast(`Cleared ChromaDB: ${Array.isArray(data?.cleared) ? data.cleared.length : 0} location(s).`);
    } catch (error) {
      showToast(error?.response?.data?.detail || error?.message || "Failed to clear ChromaDB.", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunAndSaveConfigs = async () => {
    if (stagedConfigs.length < 1 || isDatasetMissing || isRunningStaged) return;

    setIsRunningStaged(true);
    setResults(null);
    try {
      const statuses = await Promise.all(
        stagedConfigs.map(async (staged) => {
          const current = getConfigByName(staged.name) || staged;
          if (!readyStatuses.has(current.indexingStatus)) {
            return await indexConfig(current);
          }
          return current.indexingStatus;
        })
      );

      const hasErrors = statuses.some((status) => status === "error" || !status);

      if (hasErrors) {
        showToast("Some staged configs failed to save. Fix them and try again.", "error");
        setIsQueryUnlocked(false);
      } else {
        setIsQueryUnlocked(true);
        showToast("Configs are saved. Query box is now active.");
      }
    } finally {
      setIsRunningStaged(false);
    }
  };

  const handleRun = async () => {
    if (!query.trim() || stagedConfigs.length < 1 || isLoading || isDatasetMissing) return;
    if (hasPendingIndexing) {
      showToast("Wait until all staged configs are ready before running.", "warning");
      return;
    }

    setIsLoading(true);
    setResults(null);

    try {
      const payload = {
        query: query.trim(),
        configs: stagedConfigs.map((config) => {
          const current = getConfigByName(config.name) || config;
          return {
            name: current.name,
            chunk_strategy: current.chunk_strategy,
            chunk_params: current.chunk_params || {},
            embedding_provider: current.embedding_provider,
            embedding_model: current.embedding_model,
            top_k: Number(current.top_k),
            threshold: Number(current.threshold),
            collection_name: current.collection_name,
          };
        }),
      };

      const { data } = await compareConfigs(payload);
      setResults(Array.isArray(data?.results) ? data.results : []);
      showToast("Comparison complete.");
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || "Failed to run comparison.";
      showToast(detail, "error");
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-5 px-4 sm:px-6 py-6">
      {toast && (
        <div
          className={`fixed right-4 top-4 z-50 rounded-lg border px-4 py-2.5 text-xs font-mono font-medium shadow-md ${
            toast.type === "error"
              ? "border-red-500/30 bg-zinc-950 text-red-400"
              : toast.type === "warning"
                ? "border-amber-500/30 bg-zinc-950 text-amber-300"
                : "border-emerald-500/30 bg-zinc-950 text-emerald-400"
          }`}
        >
          {toast.message}
        </div>
      )}

      <DatasetBanner activeDataset={activeDataset} isDisabled={isDatasetMissing} />

      {/* Dataset & Document Selection Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">Dataset Document Selection</h2>
            <p className="text-xs text-zinc-400 mt-0.5">Upload a new document or load an existing file to evaluate pipelines.</p>
          </div>
          <Button onClick={() => setShowUploadModal(true)} disabled={isUploading || isLoading} variant="secondary" size="sm">
            {isUploading ? `Uploading… ${uploadProgress}%` : "Upload Document"}
          </Button>
        </div>
        <div>
          <DocumentPicker
            values={docIds && docIds.length > 0 ? docIds : (activeDocId ? [String(activeDocId)] : [])}
            multiSelect
            onSelectMany={(docs) => {
              const ids = (docs || []).map((doc) => String(doc.id));
              setDocIds(ids);
              setDocId(ids[0] || null);
              const names = (docs || []).map((doc) => doc.filename).join(", ");
              setFilename(names || null);
              showToast(
                docs?.length
                  ? `Selected ${docs.length} document(s) for comparison.`
                  : "Cleared document selection.",
                docs?.length ? "success" : "warning"
              );
            }}
            disabled={isUploading || isLoading || isRunningStaged}
            label="Select Document(s) for Comparison"
          />
        </div>
      </div>

      <UploadDocumentsModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleUpload}
        uploading={isUploading}
        progress={uploadProgress}
        allowMultiple
        title="Upload documents for Compare"
      />

      {/* Pipeline Library Grid */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">Pipeline Configuration Library</h2>
            <p className="text-xs text-zinc-400 mt-0.5">Presets and custom parameter sets indexed into isolated vector collections.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setShowConfigModal(true)} disabled={isDatasetMissing || isLoading} variant="secondary" size="sm">
              + Custom Config
            </Button>
            <Button onClick={handleClearChromaDb} disabled={isLoading || isUploading} variant="danger" size="sm">
              Clear ChromaDB
            </Button>
          </div>
        </div>
        <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
          {availableConfigs.map((config) => (
            <ConfigCard
              key={config.name}
              config={config}
              isStaged={stagedLookup.has(config.name)}
              onAdd={() => handleAddConfig(config)}
              disabled={isDatasetMissing || isLoading}
            />
          ))}
        </div>
      </div>

      <StagingPanel
        stagedConfigs={stagedConfigsLive}
        onRemove={handleRemoveConfig}
        onClearAll={handleClearAll}
        onRunStaged={handleRunAndSaveConfigs}
        isRunningStaged={isRunningStaged}
        isRunEnabled={!isDatasetMissing && !isLoading && !isRunningStaged && stagedConfigs.length > 0}
        isDisabled={isDatasetMissing || isLoading}
      />

      <QueryInput
        query={query}
        onChange={setQuery}
        onRun={handleRun}
        isLoading={isLoading}
        isDisabled={isUiBlocked}
        stagedCount={stagedConfigs.length}
        isActivated={isQueryUnlocked}
      />

      <div ref={resultsRef}>
        <ResultsGrid
          results={results}
          isLoading={isLoading}
          query={query}
          onUpdateResults={setResults}
        />
      </div>

      {showConfigModal && (
        <ConfigFormModal
          onSave={handleSaveCustomConfig}
          onCancel={() => setShowConfigModal(false)}
          existingNames={availableConfigs.map((config) => config.name)}
          isDisabled={isDatasetMissing || isLoading}
        />
      )}
    </div>
  );

}

