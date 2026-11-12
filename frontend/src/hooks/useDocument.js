import { useState, useCallback, useEffect, useRef } from "react";
import { uploadDocument, getChunks } from "../services/api";

export function useDocument() {
  const [document,       setDocument]       = useState(null);
  const [chunks,         setChunks]         = useState([]);
  const [uploading,      setUploading]      = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loadingChunks,  setLoadingChunks]  = useState(false);
  const [error,          setError]          = useState(null);

  const isMountedRef = useRef(true);
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const upload = useCallback(async (fileOrFiles) => {
    const files = Array.isArray(fileOrFiles) ? fileOrFiles : [fileOrFiles];
    const validFiles = files.filter(Boolean);
    if (!validFiles.length) return;

    setUploading(true);
    setError(null);
    setUploadProgress(0);
    try {
      let lastUploaded = null;
      for (let index = 0; index < validFiles.length; index += 1) {
        const file = validFiles[index];
        const fd = new FormData();
        fd.append("file", file);
        const { data } = await uploadDocument(fd, (progress) => {
          if (!isMountedRef.current) return;
          const current = Math.max(0, Math.min(100, Number(progress) || 0));
          const overall = ((index + current / 100) / validFiles.length) * 100;
          setUploadProgress(Math.round(overall));
        });
        lastUploaded = data;
      }
      if (isMountedRef.current && lastUploaded) {
        setDocument(lastUploaded);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err?.response?.data?.detail || err?.message || "Upload failed");
      }
      console.error("Upload error:", err);
    } finally {
      if (isMountedRef.current) {
        setUploading(false);
      }
    }
  }, []);

  const fetchChunks = useCallback(async (docId, configId) => {
    setLoadingChunks(true);
    setError(null);
    try {
      const { data } = await getChunks(docId, configId);
      if (!isMountedRef.current) return;
      const chunkData = data?.chunks ?? data;
      setChunks(Array.isArray(chunkData) ? chunkData : []);
    } catch (e) {
      console.error("[Chunks] Error:", e);
      if (!isMountedRef.current) return;
      setChunks([]);
      setError(e?.response?.data?.detail || e?.message || "Failed to fetch chunks");
    } finally {
      if (isMountedRef.current) {
        setLoadingChunks(false);
      }
    }
  }, []);

  const clearDocument = useCallback(() => {
    setDocument(null);
    setChunks([]);
    setError(null);
  }, []);

  const selectDocument = useCallback((doc) => {
    setDocument(doc || null);
    setError(null);
  }, []);

  return {
    document,
    chunks,
    uploading,
    uploadProgress,
    loadingChunks,
    error,
    upload,
    fetchChunks,
    clearDocument,
    selectDocument,
  };
}
