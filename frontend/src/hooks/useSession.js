import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "rag_lab_session";

const EMPTY_SESSION = { docId: null, configId: null, filename: null };

function loadInitialSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_SESSION;
    const parsed = JSON.parse(raw);
    return {
      docId: parsed?.docId || null,
      configId: parsed?.configId || null,
      filename: parsed?.filename || null,
    };
  } catch {
    return EMPTY_SESSION;
  }
}

export function useSession() {
  const [session, setSession] = useState(loadInitialSession);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  }, [session]);

  const setDocId = useCallback((docId) => {
    setSession((prev) => ({ ...prev, docId }));
  }, []);

  const setConfigId = useCallback((configId) => {
    setSession((prev) => ({ ...prev, configId }));
  }, []);

  const setFilename = useCallback((filename) => {
    setSession((prev) => ({ ...prev, filename }));
  }, []);

  const clear = useCallback(() => {
    setSession({ docId: null, configId: null, filename: null });
  }, []);

  return {
    docId: session.docId,
    configId: session.configId,
    filename: session.filename,
    setDocId,
    setConfigId,
    setFilename,
    clear,
  };
}
