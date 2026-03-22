import { useRef, useState } from "react";
import { ProgressBar } from "../common/index";

const ACCEPTED = [".pdf", ".txt", ".epub"];

export default function DocumentUpload({ document, onUpload, onClear, uploading, progress }) {
  const inputRef  = useRef();
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  };

  const handleChange = (e) => {
    const file = e.target.files[0];
    if (file) onUpload(file);
  };

  // ── Already uploaded ──────────────────────────────────────────
  if (document) {
    return (
      <div className="rounded-xl border-2 border-green-400 bg-green-50 p-6 text-center space-y-2">
        <div className="text-3xl">✅</div>
        <p className="font-semibold text-green-800">{document.filename}</p>
        <p className="text-sm text-green-600">Ready. Click <strong>Next</strong> to configure chunking.</p>
        <button onClick={onClear} className="text-xs text-gray-400 underline mt-1">
          Upload a different file
        </button>
      </div>
    );
  }

  // ── Uploading ─────────────────────────────────────────────────
  if (uploading) {
    return (
      <div className="rounded-xl border-2 border-blue-200 bg-blue-50 p-6 space-y-3">
        <p className="text-sm text-blue-700 font-medium">Uploading…</p>
        <ProgressBar value={progress} color="blue" />
        <p className="text-xs text-blue-400">{progress}%</p>
      </div>
    );
  }

  // ── Drop zone ─────────────────────────────────────────────────
  return (
    <div
      onClick={() => inputRef.current.click()}
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      className={`rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-all
        ${dragOver ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"}`}
    >
      <input ref={inputRef} type="file" accept={ACCEPTED.join(",")} className="hidden" onChange={handleChange} />
      <div className="text-4xl mb-3">📄</div>
      <p className="font-medium text-gray-700">Drop your file here or <span className="text-blue-600 underline">browse</span></p>
      <p className="text-xs text-gray-400 mt-1">Supported: PDF, TXT, EPUB</p>
    </div>
  );
}
