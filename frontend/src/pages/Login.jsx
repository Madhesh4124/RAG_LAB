import React, { useState } from 'react';
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Button, InlineAlert } from "../components/common/index";
import { IconArrowRight } from "../components/common/Icons";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, signup } = useAuth();

  const [mode, setMode] = useState("login");
  const [identifier, setIdentifier] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showNoticeModal, setShowNoticeModal] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);

  const nextPath = location.state?.from || "/mode-select";

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "signup") {
        await signup({ username: username.trim(), email: email.trim(), password });
      } else {
        await login({ identifier: identifier.trim(), password });
      }
      navigate(nextPath, { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const useSampleAccount = () => {
    setMode("login");
    setIdentifier("sample");
    setPassword("sample");
    setError("");
  };

  const handleCopyEmail = () => {
    navigator.clipboard?.writeText("madhesh4124@gmail.com");
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  const inputClass =
    "w-full rounded-lg bg-zinc-900 border border-zinc-800 px-3.5 py-2 text-xs text-zinc-100 " +
    "placeholder-zinc-500 outline-none " +
    "focus:border-amber-500/80 focus:ring-1 focus:ring-amber-500/40 transition-colors";

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center px-4 py-12 bg-zinc-950">
      <div className="w-full max-w-sm">
        {/* Brand header */}
        <div className="text-center mb-6">
          <div className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-900 border border-zinc-800 mb-3">
            <span className="font-mono text-sm font-bold text-amber-500">R</span>
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-100">
            {mode === "signup" ? "Create an account" : "Sign in to RAG Lab"}
          </h1>
          <p className="mt-1 text-xs text-zinc-500">
            {mode === "signup"
              ? "Set up your workspace to index and evaluate documents."
              : "Enter your credentials to access the laboratory."}
          </p>
        </div>

        {/* Note / System Notice Pill Button */}
        <div className="flex justify-center mb-4">
          <button
            type="button"
            onClick={() => setShowNoticeModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-xs text-amber-300 transition-all cursor-pointer shadow-xs hover:scale-[1.02] active:scale-[0.98]"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span className="font-medium">Free Tier Models & Quotas</span>
            <span className="text-[10px] bg-amber-500/25 px-1.5 py-0.5 rounded text-amber-200">Read Note ↗</span>
          </button>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 shadow-sm">
          {/* Quick demo credentials banner */}
          <div className="mb-5 rounded-lg border border-zinc-800/80 bg-zinc-950/60 p-3 flex items-center justify-between text-xs">
            <div className="font-mono text-[11px] text-zinc-400">
              <span className="text-zinc-500">Demo:</span> sample / sample
            </div>
            <button
              type="button"
              onClick={useSampleAccount}
              className="text-[11px] font-medium text-amber-400 hover:text-amber-300 transition-colors cursor-pointer"
            >
              Fill demo
            </button>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-zinc-950 p-1 mb-5 border border-zinc-800/60">
            <button
              type="button"
              onClick={() => { setMode("login"); setError(""); }}
              className={`py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                mode === "login" ? "bg-zinc-800 text-zinc-100 font-semibold" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode("signup"); setError(""); }}
              className={`py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                mode === "signup" ? "bg-zinc-800 text-zinc-100 font-semibold" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Sign Up
            </button>
          </div>

          {/* Form */}
          <form className="space-y-3.5" onSubmit={submit}>
            {mode === "signup" ? (
              <>
                <div>
                  <label className="block text-[11px] font-medium text-zinc-400 mb-1.5">Username</label>
                  <input
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className={inputClass}
                    placeholder="Enter username"
                    required
                    autoComplete="username"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-zinc-400 mb-1.5">Email address</label>
                  <input
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className={inputClass}
                    placeholder="name@example.com"
                    type="email"
                    required
                    autoComplete="email"
                  />
                </div>
              </>
            ) : (
              <div>
                <label className="block text-[11px] font-medium text-zinc-400 mb-1.5">Username or email</label>
                <input
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  className={inputClass}
                  placeholder="username or email"
                  required
                  autoComplete="username"
                />
              </div>
            )}

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[11px] font-medium text-zinc-400">Password</label>
                {mode === "login" && (
                  <button
                    type="button"
                    onClick={() => navigate("/password-reset")}
                    className="text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
                placeholder="••••••••"
                type="password"
                required
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
              />
            </div>

            {error && <InlineAlert type="error">{error}</InlineAlert>}

            <Button
              type="submit"
              disabled={loading}
              className="w-full mt-2"
              trailingIcon={!loading ? <IconArrowRight size={13} /> : null}
            >
              {loading ? "Authenticating…" : mode === "signup" ? "Create Account" : "Sign In"}
            </Button>
          </form>

          {/* Note button link in card footer */}
          <div className="mt-4 pt-3.5 border-t border-zinc-800/80 text-center">
            <button
              type="button"
              onClick={() => setShowNoticeModal(true)}
              className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-amber-300 transition-colors cursor-pointer group"
            >
              <span>💡</span>
              <span className="underline underline-offset-2">Note: Free-tier models & quota limits</span>
              <span className="text-[10px] text-zinc-500 group-hover:text-amber-300">↗</span>
            </button>
          </div>
        </div>
      </div>

      {/* Free Tier Notice Modal Window */}
      {showNoticeModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xl animate-fade-in"
          onClick={() => setShowNoticeModal(false)}
        >
          <div
            className="w-full max-w-md animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Double-bezel outer shell */}
            <div className="p-1.5 rounded-[2rem] bg-white/[0.04] border border-white/[0.16] shadow-glass-strong">
              {/* Inner core */}
              <div className="rounded-[calc(2rem-0.375rem)] bg-zinc-900/95 p-6 shadow-2xl border border-white/[0.05] space-y-5">
                {/* Header */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 text-lg flex-shrink-0">
                      💡
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-zinc-100">Free Tier Models & Quotas</h3>
                      <p className="text-xs text-zinc-400">Important infrastructure & latency notice</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowNoticeModal(false)}
                    className="w-8 h-8 flex items-center justify-center rounded-full bg-white/[0.06] border border-white/[0.08] text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.12] transition-colors cursor-pointer flex-shrink-0"
                    aria-label="Close notice modal"
                  >
                    ✕
                  </button>
                </div>

                {/* Section 1: Free Tier & Latency */}
                <div className="rounded-xl border border-white/[0.08] bg-zinc-950/60 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-amber-400">
                    <span>⚡</span>
                    <span>Free Tier APIs & Response Latency</span>
                  </div>
                  <p className="text-xs text-zinc-300 leading-relaxed">
                    All generation, embedding, and evaluation tasks in this lab are executed via <strong>free-tier community APIs</strong> (NVIDIA NIM and Groq) using developer quotas.
                  </p>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    Because these calls utilize shared free-tier infrastructure, you may experience varying response latency, token pacing, or brief cold starts.
                  </p>
                </div>

                {/* Section 2: Rate Limit / Recycle Keys */}
                <div className="rounded-xl border border-amber-500/25 bg-amber-950/20 p-4 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-amber-300">
                    <span>📬</span>
                    <span>Quota Limit Exceeded or Model Unavailable?</span>
                  </div>
                  <p className="text-xs text-zinc-300 leading-relaxed">
                    If you run into a <strong>429 Rate Limit Exceeded</strong>, <strong>Model Not Available</strong>, or API quota error, please reach out directly:
                  </p>

                  <div className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-zinc-950/80 border border-white/[0.08]">
                    <span className="font-mono text-xs text-amber-300 select-all truncate">
                      madhesh4124@gmail.com
                    </span>
                    <button
                      type="button"
                      onClick={handleCopyEmail}
                      className="px-2.5 py-1 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-[11px] font-medium border border-amber-500/30 transition-colors cursor-pointer flex-shrink-0"
                    >
                      {copiedEmail ? "✓ Copied" : "Copy Email"}
                    </button>
                  </div>

                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    Send me an email and I will promptly recycle the API keys, refresh quotas, and update the endpoints to the latest active models!
                  </p>
                </div>

                {/* Footer Action button */}
                <div className="pt-1">
                  <Button
                    type="button"
                    variant="primary"
                    className="w-full justify-center"
                    onClick={() => setShowNoticeModal(false)}
                  >
                    Got it, continue
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
