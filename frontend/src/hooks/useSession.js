import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "rag_lab_session_v2";

const EMPTY_SESSION = {
  docId: null,
  docIds: [],
  configId: null,
  filename: null,
  mode: null,
  stagedConfigs: [],
  isQueryUnlocked: false,
};

function loadInitialSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_SESSION;
    const parsed = JSON.parse(raw);
    return {
      docId: parsed?.docId || null,
      docIds: Array.isArray(parsed?.docIds) ? parsed.docIds.map((id) => String(id)) : [],
      configId: parsed?.configId || null,
      filename: parsed?.filename || null,
      mode: parsed?.mode || null,
      stagedConfigs: Array.isArray(parsed?.stagedConfigs) ? parsed.stagedConfigs : [],
      isQueryUnlocked: Boolean(parsed?.isQueryUnlocked),
    };
  } catch {
    return EMPTY_SESSION;
  }
}

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [session, setSession] = useState(loadInitialSession);

  // Sync to localStorage whenever session updates
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } catch (e) {
      console.error("Failed to save session to localStorage", e);
    }
  }, [session]);

  const setDocId = useCallback((docId) => {
    setSession((prev) => (prev.docId === docId ? prev : { ...prev, docId }));
  }, []);

  const setConfigId = useCallback((configId) => {
    setSession((prev) => (prev.configId === configId ? prev : { ...prev, configId }));
  }, []);

  const setDocIds = useCallback((docIds) => {
    const normalized = Array.isArray(docIds) ? docIds.map((id) => String(id)) : [];
    setSession((prev) => {
      if (
        prev.docIds.length === normalized.length &&
        prev.docIds.every((id, idx) => id === normalized[idx])
      ) {
        return prev;
      }
      return { ...prev, docIds: normalized };
    });
  }, []);

  const setFilename = useCallback((filename) => {
    setSession((prev) => (prev.filename === filename ? prev : { ...prev, filename }));
  }, []);

  const setMode = useCallback((mode) => {
    setSession((prev) => (prev.mode === mode ? prev : { ...prev, mode }));
  }, []);

  const setStagedConfigs = useCallback((updaterOrArray) => {
    setSession((prev) => {
      const nextStaged = typeof updaterOrArray === "function" ? updaterOrArray(prev.stagedConfigs) : updaterOrArray;
      return { ...prev, stagedConfigs: Array.isArray(nextStaged) ? nextStaged : [] };
    });
  }, []);

  const setIsQueryUnlocked = useCallback((isUnlocked) => {
    setSession((prev) => ({ ...prev, isQueryUnlocked: Boolean(isUnlocked) }));
  }, []);

  const clear = useCallback(() => {
    setSession(EMPTY_SESSION);
  }, []);

  const value = {
    docId: session.docId,
    docIds: session.docIds,
    configId: session.configId,
    filename: session.filename,
    mode: session.mode,
    stagedConfigs: session.stagedConfigs,
    isQueryUnlocked: session.isQueryUnlocked,
    setDocId,
    setDocIds,
    setConfigId,
    setFilename,
    setMode,
    setStagedConfigs,
    setIsQueryUnlocked,
    clear,
  };

  return React.createElement(SessionContext.Provider, { value }, children);
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    // Fallback if rendered outside provider during test or hot-reload
    return {
      docId: null,
      docIds: [],
      configId: null,
      filename: null,
      mode: null,
      stagedConfigs: [],
      isQueryUnlocked: false,
      setDocId: () => {},
      setDocIds: () => {},
      setConfigId: () => {},
      setFilename: () => {},
      setMode: () => {},
      setStagedConfigs: () => {},
      setIsQueryUnlocked: () => {},
      clear: () => {},
    };
  }
  return context;
}
