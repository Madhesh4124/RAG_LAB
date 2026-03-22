// pages/Compare.jsx  ──  feature/compare-mode branch
import { useSearchParams } from "react-router-dom";
import CompareMode from "../components/comparison/CompareMode";

export default function Compare() {
  const [params] = useSearchParams();
  const docId    = params.get("doc");

  return <CompareMode documentId={docId} />;
}