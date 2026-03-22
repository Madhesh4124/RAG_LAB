// pages/Setup.jsx  ──  feature/frontend-wizard branch
import { useNavigate } from "react-router-dom";
import ConfigWizard from "../components/config/ConfigWizard";

export default function Setup() {
  const navigate = useNavigate();

  const handleComplete = ({ config, documentId }) => {
    // TODO: navigate to chunk preview or chat after pipeline built
    navigate(`/preview?doc=${documentId}`);
  };

  return <ConfigWizard onComplete={handleComplete} />;
}
