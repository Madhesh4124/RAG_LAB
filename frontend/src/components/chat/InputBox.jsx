import { useState } from "react";
import { Button } from "../common/index";

export default function InputBox({ onSend, loading }) {
  const [text, setText] = useState("");

  const handleSend = () => {
    if (!text.trim() || loading) return;
    onSend(text.trim());
    setText("");
  };

  return (
    <div className="flex gap-3 pt-4 border-t border-gray-200">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
        placeholder="Ask something about your document…"
        disabled={loading}
        className="flex-1 rounded-lg border border-gray-200 px-4 py-2.5 text-sm
          focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
      />
      <Button onClick={handleSend} disabled={!text.trim() || loading}>
        {loading ? "Thinking…" : "Send →"}
      </Button>
    </div>
  );
}