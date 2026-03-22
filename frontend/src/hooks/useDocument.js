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
    } catch {
      // TODO: remove mock once backend is live
      setDocument({ id: "mock-doc-1", filename: file.name });
    } finally {
      setUploading(false);
    }
  }, []);

  const fetchChunks = useCallback(async (docId, chunkingConfig) => {
    setLoadingChunks(true);
    try {
      const { data } = await getChunks(docId, chunkingConfig);
      setChunks(data);
    } catch {
      // TODO: remove mock once backend is live
      setChunks(MOCK_CHUNKS);
    } finally {
      setLoadingChunks(false);
    }
  }, []);

  const clearDocument = () => { setDocument(null); setChunks([]); };

  return { document, chunks, uploading, uploadProgress, loadingChunks, error, upload, fetchChunks, clearDocument };
}
