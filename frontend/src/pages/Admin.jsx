import React, { useEffect, useMemo, useState } from "react";
import { Button, EyebrowTag, Badge } from "../components/common/index";
import { clearChromaRoot, deleteChromaCollection, listChromaRoots, viewChromaCollection } from "../services/api";

function truncate(text, max = 90) {
  const value = String(text || "");
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

export default function Admin() {
  const [roots,              setRoots]              = useState([]);
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [loading,            setLoading]            = useState(true);
  const [busyKey,            setBusyKey]            = useState("");
  const [error,              setError]              = useState("");

  const refresh = async () => {
    setLoading(true); setError("");
    try {
      const { data } = await listChromaRoots();
      setRoots(Array.isArray(data) ? data : []);
      if (selectedCollection) {
        const selectedName = selectedCollection?.name;
        const stillExists = (data || []).some((root) => (root.collections || []).some((c) => c.name === selectedName));
        if (!stillExists) setSelectedCollection(null);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to load Chroma data");
    } finally { setLoading(false); }
  };

  useEffect(() => { void refresh(); }, []);

  const stats = useMemo(() => {
    const collectionCount = roots.reduce((t, r) => t + (r.collections?.length || 0), 0);
    const vectorCount     = roots.reduce((t, r) => t + (r.collections || []).reduce((s, c) => s + (c.count || 0), 0), 0);
    return { collectionCount, vectorCount };
  }, [roots]);

  const handleView = async (collectionName) => {
    setBusyKey(`view:${collectionName}`); setError("");
    try {
      const { data } = await viewChromaCollection(collectionName);
      setSelectedCollection({ name: collectionName, roots: Array.isArray(data) ? data : [] });
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to load collection details");
    } finally { setBusyKey(""); }
  };

  const handleDeleteCollection = async (collectionName, rootPath = null) => {
    if (!window.confirm(`Delete collection ${collectionName}?`)) return;
    setBusyKey(`delete:${collectionName}:${rootPath || "all"}`); setError("");
    try { await deleteChromaCollection(collectionName, rootPath); await refresh(); }
    catch (err) { setError(err?.response?.data?.detail || err?.message || "Failed to delete collection"); }
    finally { setBusyKey(""); }
  };

  const handleClearRoot = async (rootPath) => {
    if (!window.confirm(`Clear all Chroma data under ${rootPath}?`)) return;
    setBusyKey(`root:${rootPath}`); setError("");
    try { await clearChromaRoot(rootPath); await refresh(); }
    catch (err) { setError(err?.response?.data?.detail || err?.message || "Failed to clear storage root"); }
    finally { setBusyKey(""); }
  };

  const handleClearAllRoots = async () => {
    if (!window.confirm("Clear ALL Chroma data roots? This will remove every stored collection shown here.")) return;
    setBusyKey("root:all"); setError("");
    try { await clearChromaRoot(); await refresh(); }
    catch (err) { setError(err?.response?.data?.detail || err?.message || "Failed to clear storage roots"); }
    finally { setBusyKey(""); }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Header card */}
      <div className="p-1.5 rounded-[2rem] bg-white/[0.04] border border-white/[0.16] reveal">
        <div className="rounded-[calc(2rem-0.375rem)] bg-surface-1 p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <EyebrowTag>System</EyebrowTag>
              <h1 className="mt-2 text-3xl font-extrabold text-white tracking-tight">Admin Controls</h1>
              <p className="mt-1 text-sm text-white/65 leading-relaxed">
                Inspect and manage stored Chroma collections across local persistence roots.
              </p>
            </div>
            <Button variant="danger" onClick={() => void handleClearAllRoots()} disabled={busyKey === "root:all"}>
              {busyKey === "root:all" ? "Clearing…" : "Clear All Roots"}
            </Button>
          </div>

          {/* Stats row */}
          <div className="mt-6 grid grid-cols-3 gap-3">
            {[
              { label: "Storage Roots", value: roots.length },
              { label: "Collections",   value: stats.collectionCount },
              { label: "Stored Chunks", value: stats.vectorCount },
            ].map(({ label, value }) => (
              <div key={label}
                className="rounded-2xl bg-surface-2 border border-white/[0.16] px-4 py-3
                  shadow-[inset_0_1px_1px_rgba(255,255,255,0.04)]">
                <span className="block text-[10px] uppercase tracking-[0.15em] font-semibold text-white/60 mb-1">
                  {label}
                </span>
                <span className="text-2xl font-extrabold text-white">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-2xl bg-red-500/[0.08] border border-red-500/[0.15] px-5 py-4 text-sm text-red-400 reveal">
          {error}
        </div>
      )}

      {/* Collections grid */}
      {loading ? (
        <div className="p-1.5 rounded-[2rem] bg-white/[0.04] border border-white/[0.16]">
          <div className="rounded-[calc(2rem-0.375rem)] bg-surface-1 p-8 text-center text-sm text-white/60
            shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-white/[0.05] border-t-accent-violet mb-3" />
            Loading Chroma details…
          </div>
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
          {/* Left: roots */}
          <div className="space-y-4">
            {roots.map((root, ri) => (
              <div key={root.root_path}
                className="p-1.5 rounded-[2rem] bg-white/[0.04] border border-white/[0.16] reveal"
                style={{ animationDelay: `${ri * 60}ms` }}>
                <div className="rounded-[calc(2rem-0.375rem)] bg-surface-1 p-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                  <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
                    <div>
                      <p className="font-bold text-white text-sm break-all leading-snug">{root.root_path}</p>
                      <p className="text-[11px] text-white/50 mt-1">{root.collections.length} collection(s)</p>
                    </div>
                    <Button variant="danger" onClick={() => void handleClearRoot(root.root_path)}
                      disabled={busyKey === `root:${root.root_path}`}>
                      Clear Root
                    </Button>
                  </div>

                  <div className="space-y-2">
                    {root.collections.length ? root.collections.map((collection) => (
                      <div key={`${root.root_path}:${collection.name}`}
                        className="rounded-2xl bg-surface-2 border border-white/[0.16] px-4 py-3
                          hover:border-white/[0.16] transition-colors duration-300">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-white text-sm truncate">{collection.name}</p>
                            <p className="text-[11px] text-white/50 mt-0.5">{collection.count} chunk(s)</p>
                            {Object.keys(collection.metadata || {}).length > 0 && (
                              <p className="text-[10px] text-white/40 mt-1 break-all">
                                {truncate(JSON.stringify(collection.metadata), 120)}
                              </p>
                            )}
                          </div>
                          <div className="flex gap-2 flex-shrink-0">
                            <Button variant="secondary" onClick={() => void handleView(collection.name)}
                              disabled={busyKey === `view:${collection.name}`}>
                              View
                            </Button>
                            <Button variant="danger" onClick={() => void handleDeleteCollection(collection.name, root.root_path)}
                              disabled={busyKey === `delete:${collection.name}:${root.root_path}`}>
                              Delete
                            </Button>
                          </div>
                        </div>
                      </div>
                    )) : (
                      <p className="text-sm text-white/60 italic">No collections stored in this root.</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Right: collection details sticky panel */}
          <div className="p-1.5 rounded-[2rem] bg-white/[0.04] border border-white/[0.16] h-fit xl:sticky xl:top-24 reveal">
            <div className="rounded-[calc(2rem-0.375rem)] bg-surface-1 p-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
              <p className="text-[10px] uppercase tracking-[0.15em] font-semibold text-white/60 mb-3">Collection Details</p>
              {!selectedCollection ? (
                <div className="py-8 text-center">
                  <div className="mx-auto w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mb-3">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-white/40">
                      <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                    </svg>
                  </div>
                  <p className="text-sm text-white/60">Select View on a collection to inspect records.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <p className="font-bold text-white text-sm">{selectedCollection.name}</p>
                    <p className="text-[11px] text-white/50 mt-0.5">
                      Visible in {selectedCollection.roots.length} storage root(s)
                    </p>
                  </div>
                  {selectedCollection.roots.map((root) => (
                    <div key={root.root_path} className="rounded-2xl bg-surface-2 border border-white/[0.16] p-3">
                      <p className="text-[10px] font-semibold text-white/60 break-all mb-2">{root.root_path}</p>
                      {(root.collections || []).map((collection) => (
                        <div key={`${root.root_path}:${collection.name}`} className="space-y-2">
                          <p className="text-[11px] text-white/50">{collection.count} chunk(s)</p>
                          {(collection.samples || []).length ? collection.samples.map((sample) => (
                            <div key={sample.id}
                              className="rounded-xl bg-surface-3 border border-white/[0.05] p-3 text-[11px] text-white/50">
                              <p className="font-semibold text-white/80 break-all mb-1">{sample.id}</p>
                              <p className="whitespace-pre-wrap text-white/60 leading-relaxed">
                                {truncate(sample.document || "", 220)}
                              </p>
                            </div>
                          )) : (
                            <p className="text-[11px] text-white/60 italic">No sample records available.</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}