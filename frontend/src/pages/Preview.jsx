// pages/Preview.jsx  ──  feature/chunk-visualizer branch
import React from 'react';
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import ChunkVisualizer from "../components/preview/ChunkVisualizer";
import { useDocument } from "../hooks/useDocument";
import { useConfig }   from "../hooks/useConfig";
import { Button }      from "../components/common/index";
import { useNavigate } from "react-router-dom";
import { useSession } from "../hooks/useSession";

export default function Preview() {
  const [params]   = useSearchParams();
  const navigate   = useNavigate();
  const { docId: sessionDocId, configId: sessionConfigId } = useSession();
  const docId    = params.get("doc")    || sessionDocId;
  const configId = params.get("config") || sessionConfigId;
  const { chunks, loadingChunks, fetchChunks, error } = useDocument();
  const { config } = useConfig();

  useEffect(() => {
    if (docId && configId) {
      console.log(`[Preview] Loading chunks with doc=${docId}, config=${configId}`);
      fetchChunks(docId, configId);
    } else {
      console.warn("[Preview] Missing docId or configId. Doc:", docId, "Config:", configId);
    }
  }, [docId, configId]);

  return (
    <div className="w-full max-w-[96%] xl:max-w-[95%] 2xl:max-w-[1760px] mx-auto px-4 sm:px-6 lg:px-10 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b border-white/[0.08]">
        <div>
          <div className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-semibold bg-accent-violet/15 border border-accent-violet/30 text-accent-violet-light mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-violet animate-pulse" />
            Inspection & Verification
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#FCF8D8] tracking-tight">Chunk Preview</h1>
          <p className="text-[#D9DADF]/80 text-sm mt-1">
            See exactly how your document was split. Click any chunk to inspect it.
          </p>
        </div>
        <div className="flex items-center gap-2.5 flex-wrap">
          <Button variant="secondary" onClick={() => navigate("/setup")}>← Reconfigure</Button>
          <Button onClick={() => {
            const docsParam = params.get("docs");
            navigate(`/custom-chat?doc=${docId}&config=${configId}${docsParam ? `&docs=${encodeURIComponent(docsParam)}` : ""}`);
          }}>
            Start Chatting →
          </Button>
          <Button variant="secondary" onClick={() => navigate(`/compare?doc=${docId}`)} trailingIcon={<span>↗</span>}>
            Try Compare Mode
          </Button>
        </div>
      </div>

      <ChunkVisualizer chunks={chunks} loading={loadingChunks} error={error} />
    </div>
  );
}
