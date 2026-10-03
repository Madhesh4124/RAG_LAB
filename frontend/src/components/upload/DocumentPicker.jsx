import React, { useEffect, useMemo, useState } from "react";
import {
  bulkDeleteDocuments,
  clearAllDocuments,
  deleteDocument,
  listDocuments,
  searchDocuments,
} from "../../services/api";

function formatFileSize(bytes) {
  if (!bytes || isNaN(bytes)) return "";
  if (bytes < 1024)           return `${bytes} B`;
  if (bytes < 1024 * 1024)    return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch { return ""; }
}

const norm = (id) => (id ? String(id).replace(/-/g, "").toLowerCase() : "");

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
  const [documents,  setDocuments]  = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState("");
  const [search,     setSearch]     = useState("");

  const load = async (query = "") => {
    setLoading(true); setError("");
    try {
      const response = query.trim()
        ? await searchDocuments(query.trim(), 100)
        : await listDocuments({ limit: 100 });
      const fetchedDocs = Array.isArray(response?.data) ? response.data : [];
      setDocuments(fetchedDocs);

      if (!query.trim() && fetchedDocs.length > 0) {
        const fetchedIds   = new Set(fetchedDocs.map((d) => norm(d.id)));
        const validValues  = (values || []).map(norm).filter((id) => fetchedIds.has(id));
        if (validValues.length !== (values || []).length) {
          if (multiSelect && onSelectMany) {
            onSelectMany(fetchedDocs.filter((d) => validValues.includes(norm(d.id))));
          } else if (!multiSelect && onSelect) {
            if (!fetchedDocs.some((d) => norm(d.id) === norm(value))) onSelect(null);
          }
        }
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to load documents");
      setDocuments([]);
    } finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, [reloadToken]);

  const handleClearSelection = () => {
    if (multiSelect && onSelectMany) onSelectMany([]);
    else if (onSelect) onSelect(null);
  };

  const handleSelectAll = () => {
    if (!multiSelect || !onSelectMany) return;
    if (values.length >= filteredDocuments.length && filteredDocuments.length > 0) onSelectMany([]);
    else onSelectMany(filteredDocuments);
  };

  const handleDelete = async (docId, docName) => {
    if (!window.confirm(`Delete "${docName || "this document"}"? This cannot be undone.`)) return;
    try {
      setLoading(true);
      await deleteDocument(docId);
      if (multiSelect && onSelectMany) {
        const current = new Set((values || []).map(norm));
        if (current.has(norm(docId))) {
          current.delete(norm(docId));
          onSelectMany(documents.filter((d) => current.has(norm(d.id)) && norm(d.id) !== norm(docId)));
        }
      } else if (!multiSelect && onSelect && norm(value) === norm(docId)) { onSelect(null); }
      await load(search);
    } catch (err) {
      alert(err?.response?.data?.detail || err?.message || "Failed to delete document");
    } finally { setLoading(false); }
  };

  const handleDeleteSelected = async () => {
    if (!values || values.length === 0) return;
    if (!window.confirm(`Permanently delete ${values.length} selected document(s)? This cannot be undone.`)) return;
    try {
      setLoading(true);
      await bulkDeleteDocuments(values);
      if (onSelectMany) onSelectMany([]);
      await load(search);
    } catch (err) {
      alert(err?.response?.data?.detail || err?.message || "Failed to delete selected documents");
    } finally { setLoading(false); }
  };

  const handleClearAllDocuments = async () => {
    if (documents.length === 0) return;
    if (!window.confirm(`Delete ALL ${documents.length} document(s)? This cannot be undone.`)) return;
    try {
      setLoading(true);
      await clearAllDocuments();
      if (multiSelect && onSelectMany) onSelectMany([]);
      else if (onSelect) onSelect(null);
      await load("");
    } catch (err) {
      alert(err?.response?.data?.detail || err?.message || "Failed to clear all documents");
    } finally { setLoading(false); }
  };

  const filteredDocuments = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? documents.filter((d) => (d.filename || "").toLowerCase().includes(q)) : documents;
  }, [documents, search]);

  const selectedDocument = useMemo(() => documents.find((doc) => norm(doc.id) === norm(value)) || null, [documents, value]);
  const selectedSet      = useMemo(() => new Set((values || []).map(norm)), [values]);
  const isAllSelected    = multiSelect && filteredDocuments.length > 0 && values.length >= filteredDocuments.length;

  return (
    <div className="rounded-3xl bg-surface-2/60 border border-white/[0.07] p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-white/80">{label}</p>
          {documents.length > 0 && (
            <span className="rounded-full bg-white/[0.06] border border-white/[0.07] px-2.5 py-0.5 text-[10px] font-semibold text-white/50">
              {documents.length}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {multiSelect && documents.length > 0 && (
            <>
              <button type="button"
                className="text-[11px] font-semibold text-accent-violet-light hover:text-white transition-colors duration-300 disabled:opacity-40"
                onClick={handleSelectAll} disabled={disabled || loading}>
                {isAllSelected ? "Deselect all" : "Select all"}
              </button>
              <span className="text-white/35 select-none">|</span>
            </>
          )}
          {documents.length > 0 && (
            <>
              <button type="button"
                className="text-[11px] font-semibold text-red-400/60 hover:text-red-400 transition-colors duration-300 disabled:opacity-40"
                onClick={handleClearAllDocuments} disabled={disabled || loading} title="Delete all uploaded documents">
                Delete all
              </button>
              <span className="text-white/35 select-none">|</span>
            </>
          )}
          <button type="button"
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-white/50 hover:text-white/60 transition-colors duration-300 disabled:opacity-40"
            onClick={() => void load(search)} disabled={disabled || loading}>
            {loading ? (
              <><span className="h-3 w-3 animate-spin rounded-full border border-white/20 border-t-accent-violet" />Refreshing</>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                </svg>
                Refresh
              </>
            )}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void load(search); } }}
            placeholder="Search by filename…"
            className="w-full rounded-2xl bg-white/[0.04] border border-white/[0.07] pl-3.5 pr-8 py-2.5 text-sm
              text-white placeholder-white/40 outline-none
              transition-all duration-400 ease-[cubic-bezier(0.32,0.72,0,1)]
              focus:border-accent-violet/40 focus:bg-white/[0.06] focus:shadow-[0_0_0_2px_rgba(221,112,11,0.14)]"
            disabled={disabled || loading}
          />
          {search && (
            <button type="button" onClick={() => { setSearch(""); void load(""); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 hover:text-white/60 transition-colors duration-200 text-xs">
              ✕
            </button>
          )}
        </div>
        <button type="button" onClick={() => void load(search)}
          className="px-4 py-2.5 text-sm font-semibold rounded-2xl bg-white/[0.05] border border-white/[0.07]
            text-white/50 hover:text-white hover:bg-white/[0.09] transition-all duration-300"
          disabled={disabled || loading}>
          Find
        </button>
      </div>

      {/* Document list */}
      <div className="rounded-2xl bg-surface-3 border border-white/[0.16] max-h-60 overflow-y-auto divide-y divide-white/[0.04]">
        {loading && documents.length === 0 ? (
          <div className="py-8 text-center text-sm text-white/50 space-y-2">
            <div className="mx-auto h-5 w-5 animate-spin rounded-full border border-white/[0.07] border-t-accent-violet" />
            <p>Loading documents…</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="py-8 px-4 text-center">
            <svg className="mx-auto h-8 w-8 text-white/[0.10] mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm font-semibold text-white/50">No documents found</p>
            <p className="text-[11px] text-white/40 mt-0.5">
              {search ? "No uploaded file matches your search." : "Upload a document above to get started."}
            </p>
          </div>
        ) : (
          filteredDocuments.map((doc) => {
            const isChecked = multiSelect ? selectedSet.has(norm(doc.id)) : norm(value) === norm(doc.id);
            const isPdf = (doc.file_type || doc.filename || "").toLowerCase().includes("pdf");
            return (
              <div key={doc.id}
                onClick={() => {
                  if (disabled || loading) return;
                  if (multiSelect) {
                    const current = new Set((values || []).map(norm));
                    if (isChecked) current.delete(norm(doc.id));
                    else current.add(norm(doc.id));
                    if (onSelectMany) onSelectMany(documents.filter((item) => current.has(norm(item.id))));
                  } else { if (onSelect) onSelect(doc); }
                }}
                className={`flex items-center justify-between px-4 py-3 cursor-pointer select-none group
                  transition-colors duration-200
                  ${isChecked ? "bg-accent-violet/[0.08] border-l-2 border-l-accent-violet/60" : "hover:bg-white/[0.04]"}`}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0 mr-3">
                  <input
                    type={multiSelect ? "checkbox" : "radio"}
                    checked={isChecked}
                    disabled={disabled || loading}
                    onChange={(e) => {
                      e.stopPropagation();
                      if (multiSelect) {
                        const current = new Set((values || []).map(norm));
                        if (e.target.checked) current.add(norm(doc.id));
                        else current.delete(norm(doc.id));
                        if (onSelectMany) onSelectMany(documents.filter((item) => current.has(norm(item.id))));
                      } else { if (onSelect) onSelect(doc); }
                    }}
                    className="h-3.5 w-3.5 accent-accent-violet"
                  />
                  <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-[9px] font-black
                    transition-transform duration-300 group-hover:scale-105
                    ${isPdf ? "bg-red-500/[0.12] text-red-400 border border-red-500/[0.15]"
                           : "bg-accent-violet/[0.10] text-accent-violet-light border border-accent-violet/[0.15]"}`}>
                    {isPdf ? "PDF" : (doc.file_type || "TXT").toUpperCase().slice(0, 3)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm truncate font-semibold ${isChecked ? "text-white" : "text-white/80"}`}
                      title={doc.filename}>
                      {doc.filename}
                    </p>
                    <div className="flex items-center gap-2 text-[10px] text-white/60 mt-0.5">
                      {doc.file_size && <span>{formatFileSize(doc.file_size)}</span>}
                      {doc.file_size && doc.upload_date && <span className="text-white/35">·</span>}
                      {doc.upload_date && <span>{formatDate(doc.upload_date)}</span>}
                    </div>
                  </div>
                </div>

                {/* Delete btn */}
                <button type="button"
                  onClick={(e) => { e.stopPropagation(); handleDelete(doc.id, doc.filename); }}
                  disabled={disabled || loading}
                  className="w-7 h-7 rounded-full flex items-center justify-center
                    text-white/40 hover:text-red-400 hover:bg-red-500/[0.08]
                    opacity-0 group-hover:opacity-100 focus:opacity-100
                    transition-all duration-300"
                  title="Delete Document">
                  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Summary footer */}
      {multiSelect ? (
        <div className="flex items-center justify-between pt-1">
          <p className="text-[11px] text-white/50">
            Selected: <span className="text-white/60 font-bold">{values.length}</span> of {documents.length}
          </p>
          {values.length > 0 && (
            <div className="flex items-center gap-3">
              <button type="button" onClick={handleClearSelection}
                className="text-[11px] font-semibold text-accent-violet-light hover:text-white transition-colors duration-200">
                Clear selection
              </button>
              <span className="text-white/35">·</span>
              <button type="button" onClick={handleDeleteSelected} disabled={disabled || loading}
                className="text-[11px] font-semibold text-red-400/60 hover:text-red-400 transition-colors duration-200 disabled:opacity-40">
                Delete ({values.length})
              </button>
            </div>
          )}
        </div>
      ) : (
        selectedDocument && (
          <div className="flex items-center justify-between px-3.5 py-2.5 rounded-2xl
            bg-accent-violet/[0.07] border border-accent-violet/[0.15]">
            <span className="text-[12px] text-white/80 font-semibold truncate">
              {selectedDocument.filename}
            </span>
            <div className="flex items-center gap-2.5 ml-2 flex-shrink-0">
              {selectedDocument.file_size && (
                <span className="text-[11px] text-accent-violet-light">{formatFileSize(selectedDocument.file_size)}</span>
              )}
              <button type="button" onClick={handleClearSelection}
                className="text-[11px] font-semibold text-red-400/60 hover:text-red-400 transition-colors duration-200">
                Clear
              </button>
            </div>
          </div>
        )
      )}

      {error && <p className="text-[11px] text-red-400 font-medium">{error}</p>}
    </div>
  );
}
