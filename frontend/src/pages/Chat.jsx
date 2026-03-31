import { useSearchParams, useNavigate } from "react-router-dom";
import ChatInterface from "../components/chat/ChatInterface";
import { Button } from "../components/common/index";

export default function Chat() {
  const [params]  = useSearchParams();
  const navigate  = useNavigate();

const docId     = params.get("doc");
const configId  = params.get("config");

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chat</h1>
          <p className="text-sm text-gray-400 mt-1">Ask questions about your document.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate(`/preview?doc=${docId}&config=${configId}`)}>
            ← Chunk Preview
          </Button>
          <Button onClick={() => navigate(`/compare?doc=${docId}`)}>
            Compare Mode →
          </Button>
        </div>
      </div>
      <ChatInterface docId={docId} configId={configId} />
    </div>
  );
}
   