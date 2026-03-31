import { useSearchParams } from "react-router-dom";
import CompareMode from "../components/comparison/CompareMode";
import { useSession } from "../hooks/useSession";

export default function Compare() {
  const [params] = useSearchParams();
  const { docId: sessionDocId } = useSession();
  const docId = params.get("doc") || sessionDocId;

  return <CompareMode documentId={docId} />;
}