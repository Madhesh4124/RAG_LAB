// pages/Preview.jsx  ──  feature/chunk-visualizer branch
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import ChunkVisualizer from "../components/preview/ChunkVisualizer";
import { useDocument } from "../hooks/useDocument";
import { useConfig }   from "../hooks/useConfig";
import { Button }      from "../components/common/index";
import { useNavigate } from "react-router-dom";

export default function Preview() {
  const [params]   = useSearchParams();
  const docId      = params.get("doc");
  const navigate   = useNavigate();

  const { chunks, loadingChunks, fetchChunks } = useDocument();
  const { config } = useConfig();

  useEffect(() => {
    if (docId) fetchChunks(docId, config.chunking);
  }, [docId]);

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
          <Button onClick={() => navigate(`/chat?doc=${docId}`)}>Start Chatting →</Button>
        </div>
      </div>

      <ChunkVisualizer chunks={chunks} loading={loadingChunks} />
    </div>
  );
}
