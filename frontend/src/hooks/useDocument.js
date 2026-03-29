import { useState, useCallback } from "react";
import { uploadDocument, getChunks, MOCK_CHUNKS } from "../services/api";

export function useDocument() {
  const [document,       setDocument]       = useState(null);
  const [chunks,         setChunks]         = useState([]);
  const [uploading,      setUploading]      = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loadingChunks,  setLoadingChunks]  = useState(false);
  const [error,          setError]          = useState(null);

  const upload = useCallback(async (file) => {
    setUploading(true);
    setError(null);
    setUploadProgress(0);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await uploadDocument(fd, setUploadProgress);
      setDocument(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Upload failed");
      console.error("Upload error:", err);
    } finally {
      setUploading(false);
    }
  }, []);

  const fetchChunks = useCallback(async (docId, configId) => {
    setLoadingChunks(true);
    setError(null);
    try {
      if (!configId) {
        throw new Error("Config ID is required. Please complete the configuration wizard.");
      }
      console.log(`[Chunks] Fetching chunks for doc=${docId}, config=${configId}`);
      const { data } = await getChunks(docId, configId);
      console.log("[Chunks] Success:", data);
      setChunks(data.chunks || data);
    } catch (e) {
      const errorMsg = e.response?.data?.detail || e.message || "Failed to fetch chunks";
      console.error("[Chunks] Error:", errorMsg, e);
      setError(errorMsg);
      setChunks(MOCK_CHUNKS);
    } finally {
      setLoadingChunks(false);
    }
  }, []);

  const clearDocument = () => { setDocument(null); setChunks([]); };

  return { document, chunks, uploading, uploadProgress, loadingChunks, error, upload, fetchChunks, clearDocument };
}
