export default function MessageList({ messages }) {
  const formatMs = (value) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return "0ms";
    return `${Math.round(n)}ms`;
  };

  if (!messages.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-300">
        <div className="text-center">
          <div className="text-4xl mb-2">💬</div>
          <p className="text-sm">Ask a question about your document</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((msg, i) => (
        <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
          <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm
            ${msg.role === "user"
              ? "bg-blue-600 text-white rounded-br-sm"
              : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"}`}>
            <p className="leading-relaxed">{msg.content}</p>

            {/* Retrieved chunks */}
            {msg.chunks?.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">
                  Retrieved {msg.chunks.length} chunks
                </p>
                {msg.chunks.map((chunk, j) => (
                  <div key={j} className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
                    <div className="flex justify-between mb-1">
                      <span className="text-xs font-mono text-gray-400">#{j + 1}</span>
                      <span className="text-xs text-blue-500 font-medium">
                        score: {chunk.score?.toFixed(3)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 line-clamp-2">{chunk.text}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Timings */}
            {msg.timings && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-2">
                  Pipeline Timings
                </p>
                <div className="grid grid-cols-2 gap-1">
                  {Object.entries(msg.timings).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="text-gray-400">{key.replace("_ms", "").replace(/_/g, " ")}</span>
                      <span className="font-mono text-gray-600">{formatMs(val)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}