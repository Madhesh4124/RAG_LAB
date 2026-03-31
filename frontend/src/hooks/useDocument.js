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
    const { data } = await getChunks(docId, configId);
    const chunkData = data?.chunks || data;
    if (Array.isArray(chunkData) && chunkData.length > 0) {
      setChunks(chunkData);
    } else {
      setChunks(MOCK_CHUNKS);
    }
  } catch (e) {
    console.error("[Chunks] Error:", e);
    setChunks(MOCK_CHUNKS);
    setError(e.message);
  } finally {
    setLoadingChunks(false);
  }
}, []);

  const clearDocument = () => { setDocument(null); setChunks([]); };

  return { document, chunks, uploading, uploadProgress, loadingChunks, error, upload, fetchChunks, clearDocument };
}
