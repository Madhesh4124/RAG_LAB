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
        </div>
      </div>
    </div>
  );
}
