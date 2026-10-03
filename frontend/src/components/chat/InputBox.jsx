import React, { useState, useRef, useEffect } from "react";
import { IconSend } from "../common/Icons";

export default function InputBox({ onSend, loading }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  };

  useEffect(() => {
    autoResize();
  }, [text]);

  const handleSend = () => {
    if (!text.trim() || loading) return;
    onSend(text.trim());
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = !!text.trim() && !loading;

  return (
    <div className="pt-2">
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/90 p-2.5 transition-all focus-within:border-zinc-700 focus-within:bg-zinc-900 shadow-sm">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask a question about your indexed documents…"
          disabled={loading}
          rows={1}
          aria-label="Chat input"
          className="w-full bg-transparent text-xs text-zinc-100 placeholder-zinc-500 outline-none resize-none leading-relaxed min-h-[22px] max-h-36"
        />

        <div className="mt-2 pt-2 border-t border-zinc-800/60 flex items-center justify-between">
          <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-500">
            <span>Press <kbd className="px-1 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400">↵ Enter</kbd> to send</span>
            <span>·</span>
            <span><kbd className="px-1 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400">⇧ Shift</kbd> for newline</span>
          </div>

          <button
            onClick={handleSend}
            disabled={!canSend}
            aria-label="Send message"
            className={`flex h-7 px-3 items-center gap-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              canSend
                ? "bg-amber-500 text-zinc-950 font-semibold hover:bg-amber-400"
                : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
            }`}
          >
            {loading ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-zinc-700 border-t-amber-500" />
            ) : (
              <>
                <span>Send</span>
                <IconSend size={11} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}