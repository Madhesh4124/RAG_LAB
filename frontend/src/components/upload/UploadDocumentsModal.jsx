import React from "react";
import { useRef } from "react";
import { Button } from "../common/index";

export default function UploadDocumentsModal({
  open,
  onClose,
  onUpload,
  uploading = false,
  progress = 0,
  allowMultiple = true,
  title = "Upload Documents",
  subtitle = "Supported: PDF, TXT, EPUB",
}) {
  const inputRef = useRef(null);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4
        bg-black/60 backdrop-blur-xl"
      onClick={onClose}
    >
      {/* Double-Bezel modal */}
      <div
        className="w-full max-w-md animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Outer shell */}
        <div className="p-1.5 rounded-[2rem] bg-white/[0.04] border border-white/[0.16] shadow-glass-strong">
          {/* Inner core */}
          <div className="rounded-[calc(2rem-0.375rem)] bg-surface-1 p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.07)]">

            {/* Header */}
            <div className="flex items-start justify-between gap-4 mb-6">
              <div>
                <h3 className="text-lg font-bold text-white">{title}</h3>
                <p className="text-sm text-white/60 mt-0.5">{subtitle}</p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-full bg-white/[0.05] border border-white/[0.07]
                  text-white/65 hover:text-white hover:bg-white/[0.10]
                  transition-all duration-300 flex-shrink-0"
                aria-label="Close upload dialog"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            {/* Drop zone — Double-Bezel inner */}
            <div className="p-1 rounded-2xl bg-white/[0.02] border border-dashed border-white/[0.18]
              hover:border-accent-violet/40 transition-colors duration-500 mb-5">
              <div className="rounded-[calc(1rem-0.25rem)] bg-surface-2/60 px-6 py-10 text-center
                shadow-[inset_0_1px_1px_rgba(255,255,255,0.03)]">
                <input
                  ref={inputRef}
                  type="file"
                  multiple={allowMultiple}
                  accept=".pdf,.txt,.epub"
                  className="hidden"
                  onChange={(event) => {
                    const files = Array.from(event.target.files || []);
                    if (files.length) void onUpload(files);
                    event.target.value = "";
                  }}
                />
                {/* Upload icon */}
                <div className="mx-auto mb-4 w-12 h-12 rounded-2xl bg-accent-violet/[0.08] border border-accent-violet/[0.15]
                  flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
                    className="text-accent-violet-light">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <p className="text-sm text-white/65 mb-4">
                  {allowMultiple ? "Select one or more files to upload" : "Select a file to upload"}
                </p>
                <Button onClick={() => inputRef.current?.click()} disabled={uploading} trailingIcon={<span>↑</span>}>
                  {uploading ? `Uploading… ${progress}%` : allowMultiple ? "Choose Files" : "Choose File"}
                </Button>
              </div>
            </div>

            {/* Progress bar — visible during upload */}
            {uploading && (
              <div className="mb-5 space-y-2">
                <div className="h-1 w-full rounded-full bg-white/[0.05] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-accent-violet shadow-[0_0_8px_rgba(221,112,11,0.6)]
                      transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]"
                    style={{ width: `${Math.max(5, progress)}%` }}
                  />
                </div>
                <p className="text-[11px] text-white/50 text-right">{progress}%</p>
              </div>
            )}

            {/* Footer */}
            <div className="flex justify-end">
              <Button variant="ghost" onClick={onClose} disabled={uploading}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}