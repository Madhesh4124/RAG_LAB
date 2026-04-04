import React from "react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "../components/common/index";
import { clearChromaRoot, deleteChromaCollection, listChromaRoots, viewChromaCollection } from "../services/api";

function truncate(text, max = 90) {
  const value = String(text || "");
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

export default function Admin() {
  const [roots, setRoots] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState("");
  const [error, setError] = useState("");

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await listChromaRoots();
      setRoots(Array.isArray(data) ? data : []);
      if (selectedCollection) {
        const selectedName = selectedCollection?.name;
        const stillExists = (data || []).some((root) =>
          (root.collections || []).some((collection) => collection.name === selectedName),
        );
        if (!stillExists) setSelectedCollection(null);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to load Chroma data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const stats = useMemo(() => {
    const collectionCount = roots.reduce((total, root) => total + (root.collections?.length || 0), 0);
    const vectorCount = roots.reduce((total, root) => {
      return total + (root.collections || []).reduce((sum, collection) => sum + (collection.count || 0), 0);
    }, 0);
    return { collectionCount, vectorCount };
  }, [roots]);

  const handleView = async (collectionName) => {
    setBusyKey(`view:${collectionName}`);
    setError("");
    try {
      const { data } = await viewChromaCollection(collectionName);
      setSelectedCollection({ name: collectionName, roots: Array.isArray(data) ? data : [] });
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to load collection details");
    } finally {
      setBusyKey("");
    }
  };

  const handleDeleteCollection = async (collectionName, rootPath = null) => {
    if (!window.confirm(`Delete collection ${collectionName}?`)) return;
    setBusyKey(`delete:${collectionName}:${rootPath || "all"}`);
    setError("");
    try {
      await deleteChromaCollection(collectionName, rootPath);
      await refresh();
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to delete collection");
    } finally {
      setBusyKey("");
    }
  };

  const handleClearRoot = async (rootPath) => {
    if (!window.confirm(`Clear all Chroma data under ${rootPath}?`)) return;
    setBusyKey(`root:${rootPath}`);
    setError("");
    try {
      await clearChromaRoot(rootPath);
      await refresh();
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to clear storage root");
    } finally {
      setBusyKey("");
    }
  };

  const handleClearAllRoots = async () => {
    if (!window.confirm("Clear ALL Chroma data roots? This will remove every stored collection shown here.")) return;
    setBusyKey("root:all");
    setError("");
    try {
      await clearChromaRoot();
      await refresh();
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to clear storage roots");
    } finally {
      setBusyKey("");
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h1 className="text-2xl font-bold text-gray-900">Admin Controls</h1>
        <p className="mt-1 text-sm text-gray-500">Inspect and manage stored Chroma collections across local persistence roots.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="danger" onClick={() => void handleClearAllRoots()} disabled={busyKey === "root:all"}>
            Clear all roots
          </Button>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3 text-sm text-gray-600">
          <div className="rounded-xl bg-gray-50 p-3"><span className="block text-xs uppercase tracking-wide text-gray-400">Storage roots</span><span className="font-semibold text-gray-900">{roots.length}</span></div>
          <div className="rounded-xl bg-gray-50 p-3"><span className="block text-xs uppercase tracking-wide text-gray-400">Collections</span><span className="font-semibold text-gray-900">{stats.collectionCount}</span></div>
          <div className="rounded-xl bg-gray-50 p-3"><span className="block text-xs uppercase tracking-wide text-gray-400">Stored chunks</span><span className="font-semibold text-gray-900">{stats.vectorCount}</span></div>
        </div>
      </div>

      {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {loading ? (
        <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">Loading Chroma details…</div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1.3fr_0.9fr]">
          <div className="space-y-4">
            {roots.map((root) => (
              <div key={root.root_path} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="font-semibold text-gray-900">{root.root_path}</h2>
                    <p className="text-xs text-gray-500 mt-1">{root.collections.length} collection(s)</p>
                  </div>
                  <Button variant="danger" onClick={() => void handleClearRoot(root.root_path)} disabled={busyKey === `root:${root.root_path}`}>
                    Clear this root
                  </Button>
                </div>

                <div className="mt-4 space-y-3">
                  {root.collections.length ? root.collections.map((collection) => (
                    <div key={`${root.root_path}:${collection.name}`} className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-medium text-gray-900">{collection.name}</p>
                          <p className="text-xs text-gray-500">{collection.count} chunk(s)</p>
                          {Object.keys(collection.metadata || {}).length > 0 && (
                            <p className="mt-1 text-xs text-gray-500">Metadata: {truncate(JSON.stringify(collection.metadata), 120)}</p>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <Button variant="secondary" onClick={() => void handleView(collection.name)} disabled={busyKey === `view:${collection.name}`}>
                            View
                          </Button>
                          <Button variant="danger" onClick={() => void handleDeleteCollection(collection.name, root.root_path)} disabled={busyKey === `delete:${collection.name}:${root.root_path}`}>
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  )) : (
                    <p className="text-sm text-gray-500">No collections stored in this root.</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sticky top-4">
              <h2 className="font-semibold text-gray-900">Collection details</h2>
              {!selectedCollection ? (
                <p className="mt-3 text-sm text-gray-500">Select View on a collection to inspect sample records.</p>
              ) : (
                <div className="mt-3 space-y-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{selectedCollection.name}</p>
                    <p className="text-xs text-gray-500">Visible in {selectedCollection.roots.length} storage root(s)</p>
                  </div>
                  {selectedCollection.roots.map((root) => (
                    <div key={root.root_path} className="rounded-xl border border-gray-200 bg-gray-50 p-3">
                      <p className="text-xs font-medium text-gray-500 break-all">{root.root_path}</p>
                      {(root.collections || []).map((collection) => (
                        <div key={`${root.root_path}:${collection.name}`} className="mt-3 space-y-2">
                          <p className="text-xs text-gray-500">{collection.count} chunk(s)</p>
                          {(collection.samples || []).length ? collection.samples.map((sample) => (
                            <div key={sample.id} className="rounded-lg bg-white p-3 text-xs text-gray-600 border border-gray-200">
                              <p className="font-medium text-gray-800 break-all">{sample.id}</p>
                              <p className="mt-1 whitespace-pre-wrap">{truncate(sample.document || "", 220)}</p>
                            </div>
                          )) : (
                            <p className="text-xs text-gray-500">No sample records available.</p>
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