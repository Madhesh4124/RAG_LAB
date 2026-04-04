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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-2xl border border-gray-200 bg-white p-5 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close upload dialog"
          >
            x
          </button>
        </div>

        <div className="mt-4 rounded-xl border-2 border-dashed border-gray-300 p-8 text-center">
          <input
            ref={inputRef}
            type="file"
            multiple={allowMultiple}
            accept=".pdf,.txt,.epub"
            className="hidden"
            onChange={(event) => {
              const files = Array.from(event.target.files || []);
              if (files.length) {
                void onUpload(files);
              }
              event.target.value = "";
            }}
          />
          <p className="text-sm text-gray-600">Select one or more files to upload</p>
          <div className="mt-3">
            <Button onClick={() => inputRef.current?.click()} disabled={uploading}>
              {uploading ? `Uploading... ${progress}%` : allowMultiple ? "Choose Files" : "Choose File"}
            </Button>
          </div>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={uploading}>Close</Button>
        </div>
      </div>
    </div>
  );
}