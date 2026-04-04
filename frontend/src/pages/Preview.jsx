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
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chunk Preview</h1>
          <p className="text-sm text-gray-400 mt-1">
            See exactly how your document was split. Click any chunk to inspect it.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate("/setup")}>← Reconfigure</Button>
          <Button onClick={() => navigate(`/custom-chat?doc=${docId}&config=${configId}`)}>
            Start Chatting →
          </Button>
          <Button onClick={() => navigate(`/compare?doc=${docId}`)}>Try Compare Mode →</Button>
        </div>
      </div>

      <ChunkVisualizer chunks={chunks} loading={loadingChunks} error={error} />
    </div>
  );
}
