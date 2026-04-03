import { Badge, Button } from "../common/index";

export default function ConfigCard({ config, onAdd, isStaged, disabled }) {
  const status = config.indexingStatus || "idle";
  const statusLabel =
    status === "indexing"
      ? "Indexing..."
      : status === "ready"
        ? "Ready ✅"
        : status === "already_exists"
          ? "Already indexed ✅"
          : status === "error"
            ? "Index failed"
            : "Not indexed";

  const statusColor =
    status === "indexing"
      ? "orange"
      : status === "ready" || status === "already_exists"
        ? "green"
        : status === "error"
          ? "red"
          : "gray";

  const canAdd = !disabled && !isStaged && status !== "indexing";

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{config.name}</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge color="blue">top_k: {config.top_k}</Badge>
            <Badge color="gray">threshold: {Number(config.threshold).toFixed(2)}</Badge>
            <Badge color="orange">{config.chunk_strategy}</Badge>
            <Badge color="gray">{config.embedding_model}</Badge>
            <Badge color={statusColor}>{statusLabel}</Badge>
          </div>
        </div>
        <Button
          onClick={onAdd}
          disabled={!canAdd}
          variant={isStaged ? "secondary" : "primary"}
          className="whitespace-nowrap"
        >
          {isStaged ? "Added" : "Add ➕"}
        </Button>
      </div>
      <p className="mt-3 text-xs text-gray-400">
        {config.isPreset ? "Preset configuration" : "Custom configuration"}
      </p>
    </div>
  );
}
