import React from "react";
import { useEffect, useMemo, useState } from "react";

import { deleteDocument, listDocuments, searchDocuments } from "../../services/api";

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

  const handleDelete = async (docId) => {
    if (!window.confirm("Are you sure you want to delete this document? This action cannot be undone.")) return;
    try {
      setLoading(true);
      await deleteDocument(docId);
      
      // Update selections if the deleted doc was selected
      if (multiSelect && onSelectMany) {
        const current = new Set((values || []).map((id) => String(id)));
        if (current.has(String(docId))) {
           current.delete(String(docId));
           onSelectMany(documents.filter(d => current.has(String(d.id)) && String(d.id) !== String(docId)));
        }
      } else if (!multiSelect && onSelect && String(value) === String(docId)) {
        onSelect(null);
      }

      await load(search);
    } catch (err) {
      alert(err?.response?.data?.detail || err?.message || "Failed to delete document");
    } finally {
      setLoading(false);
    }
  };

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

      <div className="rounded-lg border border-gray-300 max-h-48 overflow-auto">
        {documents.length === 0 ? (
          <p className="px-3 py-2 text-sm text-gray-500">No documents found</p>
        ) : (
          documents.map((doc) => {
            const isChecked = multiSelect ? selectedSet.has(String(doc.id)) : String(value) === String(doc.id);
            return (
              <div key={doc.id} className="flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50 border-b border-gray-100 last:border-0 group">
                <label className="flex items-center gap-2 cursor-pointer flex-1 min-w-0 mr-2">
                  <input
                    type={multiSelect ? "checkbox" : "radio"}
                    checked={isChecked}
                    disabled={disabled || loading}
                    onChange={(e) => {
                      if (multiSelect) {
                        const current = new Set((values || []).map((id) => String(id)));
                        if (e.target.checked) current.add(String(doc.id));
                        else current.delete(String(doc.id));
                        if (onSelectMany) {
                          const nextDocs = documents.filter((item) => current.has(String(item.id)));
                          onSelectMany(nextDocs);
                        }
                      } else {
                        if (onSelect) onSelect(doc);
                      }
                    }}
                  />
                  <span className="truncate">{doc.filename}</span>
                </label>
                <button 
                  type="button" 
                  onClick={() => handleDelete(doc.id)}
                  disabled={disabled || loading}
                  className="text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 focus:opacity-100"
                  title="Delete Document"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                </button>
              </div>
            );
          })
        )}
      </div>

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
