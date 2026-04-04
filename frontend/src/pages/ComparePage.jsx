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
      embedding_model: "nvidia/nv-embed-v1",
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
  const { docId: activeDocId, filename: activeDataset, setDocId, setFilename } = useSession();
  const [availableConfigs, setAvailableConfigs] = useState(createPresetConfigs);
  const [stagedConfigs, setStagedConfigs] = useState([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunningStaged, setIsRunningStaged] = useState(false);
  const [isQueryUnlocked, setIsQueryUnlocked] = useState(false);
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

  useEffect(() => {
    activeDatasetRef.current = activeDataset;
    setAvailableConfigs(createPresetConfigs());
    setStagedConfigs([]);
    setResults(null);
    setQuery("");
    setIsQueryUnlocked(false);
    setShowConfigModal(false);
  }, [activeDataset]);

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
      const { data } = await compareIndex({
        document_id: activeDocId,
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
      }
      if (lastUploaded) {
        setDocId(lastUploaded?.id || null);
        setFilename(lastUploaded?.filename || nextFiles[nextFiles.length - 1].name);
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
      const statuses = [];
      for (const staged of stagedConfigs) {
        const current = getConfigByName(staged.name) || staged;
        if (!readyStatuses.has(current.indexingStatus)) {
          const status = await indexConfig(current);
          statuses.push(status);
        } else {
          statuses.push(current.indexingStatus);
        }
      }

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
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      {toast && (
        <div
          className={`fixed right-4 top-4 z-50 rounded-xl border px-4 py-3 text-sm shadow-lg backdrop-blur ${
            toast.type === "error"
              ? "border-red-200 bg-red-50 text-red-700"
              : toast.type === "warning"
                ? "border-amber-200 bg-amber-50 text-amber-800"
                : "border-emerald-200 bg-emerald-50 text-emerald-700"
          }`}
        >
          {toast.message}
        </div>
      )}

      <DatasetBanner activeDataset={activeDataset} isDisabled={isDatasetMissing} />

      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm md:p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Upload Document</h2>
            <p className="text-sm text-gray-500">Upload a file or load an existing document before indexing staged configs.</p>
          </div>
          <Button
            onClick={() => setShowUploadModal(true)}
            disabled={isUploading || isLoading}
            variant="secondary"
          >
            {isUploading ? `Uploading... ${uploadProgress}%` : "Upload Documents"}
          </Button>
        </div>
        {isUploading && <p className="text-sm text-blue-700">Uploading... {uploadProgress}%</p>}

        <div className="mt-4">
          <DocumentPicker
            value={activeDocId || ""}
            onSelect={(doc) => {
              setDocId(doc?.id || null);
              setFilename(doc?.filename || null);
              showToast(doc ? `Loaded "${doc.filename}".` : "Cleared document selection.", doc ? "success" : "warning");
            }}
            disabled={isUploading || isLoading || isRunningStaged}
            label="Load Previously Uploaded Document"
          />
        </div>
      </section>

      <UploadDocumentsModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleUpload}
        uploading={isUploading}
        progress={uploadProgress}
        allowMultiple
        title="Upload documents for Compare"
      />

      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm md:p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Compare Configurations</h2>
            <p className="text-sm text-gray-500">Presets and custom configs are indexed into dedicated collections before comparison.</p>
          </div>
          <Button onClick={() => setShowConfigModal(true)} disabled={isDatasetMissing || isLoading} variant="secondary">
            + Create Config
          </Button>
          <Button onClick={handleClearChromaDb} disabled={isLoading || isUploading} variant="danger">
            Clear Entire ChromaDB
          </Button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
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
      </section>

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
        <ResultsGrid results={results} isLoading={isLoading} />
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
