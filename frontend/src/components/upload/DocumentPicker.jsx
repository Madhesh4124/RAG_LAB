import React from "react";
import { useEffect, useMemo, useState } from "react";

import { listDocuments, searchDocuments } from "../../services/api";

export default function DocumentPicker({
  value,
  onSelect,
  values = [],
  onSelectMany,
  multiSelect = false,
  disabled = false,
  label = "Use previously uploaded document",
  reloadToken = 0,
}) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const load = async (query = "") => {
    setLoading(true);
    setError("");
    try {
      const response = query.trim()
        ? await searchDocuments(query.trim(), 100)
        : await listDocuments({ limit: 100 });
      setDocuments(Array.isArray(response?.data) ? response.data : []);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to load documents");
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [reloadToken]);

  const selectedDocument = useMemo(
    () => documents.find((doc) => String(doc.id) === String(value || "")) || null,
    [documents, value],
  );

  const selectedSet = useMemo(() => new Set((values || []).map((id) => String(id))), [values]);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-gray-700">{label}</p>
        <button
          type="button"
          className="text-xs text-blue-600 hover:text-blue-700"
          onClick={() => void load(search)}
          disabled={disabled || loading}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="flex gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by filename"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          disabled={disabled || loading}
        />
        <button
          type="button"
          onClick={() => void load(search)}
          className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          disabled={disabled || loading}
        >
          Find
        </button>
      </div>

      {multiSelect ? (
        <div className="rounded-lg border border-gray-300 max-h-48 overflow-auto">
          {documents.length === 0 ? (
            <p className="px-3 py-2 text-sm text-gray-500">No documents found</p>
          ) : (
            documents.map((doc) => {
              const checked = selectedSet.has(String(doc.id));
              return (
                <label key={doc.id} className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={disabled || loading}
                    onChange={(e) => {
                      const current = new Set((values || []).map((id) => String(id)));
                      if (e.target.checked) current.add(String(doc.id));
                      else current.delete(String(doc.id));
                      if (onSelectMany) {
                        const nextDocs = documents.filter((item) => current.has(String(item.id)));
                        onSelectMany(nextDocs);
                      }
                    }}
                  />
                  <span className="truncate">{doc.filename}</span>
                </label>
              );
            })
          )}
        </div>
      ) : (
        <select
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={value || ""}
          onChange={(e) => {
            const nextId = e.target.value;
            const nextDoc = documents.find((doc) => String(doc.id) === String(nextId));
            onSelect(nextDoc || null);
          }}
          disabled={disabled || loading}
        >
          <option value="">Select a document</option>
          {documents.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.filename}
            </option>
          ))}
        </select>
      )}

      {multiSelect ? (
        <p className="text-xs text-gray-500">Selected: {values.length} document(s)</p>
      ) : selectedDocument && (
        <p className="text-xs text-gray-500">
          Selected: {selectedDocument.filename}
        </p>
      )}

      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
