import React from 'react';
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

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

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white border border-gray-200 rounded-2xl shadow-sm p-6 space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">RAG Lab</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in to continue</p>
        </div>

        <div className="grid grid-cols-2 gap-2 bg-gray-100 p-1 rounded-xl">
          <button
            type="button"
            className={`rounded-lg py-2 text-sm font-medium ${mode === "login" ? "bg-white text-gray-900" : "text-gray-500"}`}
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            type="button"
            className={`rounded-lg py-2 text-sm font-medium ${mode === "signup" ? "bg-white text-gray-900" : "text-gray-500"}`}
            onClick={() => setMode("signup")}
          >
            Signup
          </button>
        </div>

        <form className="space-y-3" onSubmit={submit}>
          {mode === "signup" ? (
            <>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="Username"
                required
              />
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="Email"
                type="email"
                required
              />
            </>
          ) : (
            <input
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="Username or email"
              required
            />
          )}

          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            placeholder="Password"
            type="password"
            required
          />

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 text-white py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? "Please wait..." : mode === "signup" ? "Create Account" : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
