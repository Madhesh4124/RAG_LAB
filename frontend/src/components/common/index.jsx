import React from "react";

// ── Button ──────────────────────────────────────────────────────
export function Button({ children, onClick, variant = "primary", disabled, className = "", type = "button" }) {
  const base = "px-4 py-2 rounded-lg font-medium text-sm transition-all focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-40 disabled:cursor-not-allowed";
  const variants = {
    primary:   "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-400",
    secondary: "bg-gray-100 text-gray-700 hover:bg-gray-200 focus:ring-gray-300",
    ghost:     "text-gray-500 hover:bg-gray-100 focus:ring-gray-300",
    danger:    "bg-red-500 text-white hover:bg-red-600 focus:ring-red-400",
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </button>
  );
}

// ── Card ─────────────────────────────────────────────────────────
export function Card({ children, className = "", onClick, selected }) {
  return (
    <div onClick={onClick}
      className={`rounded-xl border bg-white p-4 shadow-sm transition-all
        ${onClick ? "cursor-pointer hover:shadow-md hover:border-blue-300" : ""}
        ${selected ? "border-blue-500 ring-2 ring-blue-100" : "border-gray-200"}
        ${className}`}>
      {children}
    </div>
  );
}

// ── ProgressBar ──────────────────────────────────────────────────
export function ProgressBar({ value, max = 100, color = "blue" }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const track = { blue: "bg-blue-500", green: "bg-green-500", orange: "bg-orange-400" }[color];
  return (
    <div className="h-1.5 w-full rounded-full bg-gray-200 overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-300 ${track}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

// ── Spinner ──────────────────────────────────────────────────────
export function Spinner({ label }) {
  return (
    <div className="flex flex-col items-center gap-2 py-8">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-blue-600" />
      {label && <p className="text-sm text-gray-400">{label}</p>}
    </div>
  );
}

// ── Badge ────────────────────────────────────────────────────────
export function Badge({ children, color = "blue" }) {
  const colors = {
    blue:   "bg-blue-100 text-blue-700",
    green:  "bg-green-100 text-green-700",
    yellow: "bg-yellow-100 text-yellow-800",
    orange: "bg-orange-100 text-orange-700",
    red:    "bg-red-100 text-red-700",
    gray:   "bg-gray-100 text-gray-500",
  };
  return <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${colors[color]}`}>{children}</span>;
}

// ── StepIndicator ────────────────────────────────────────────────
export function StepIndicator({ steps, current }) {
  return (
    <div className="flex items-center gap-1">
      {steps.map((label, i) => (
        <div key={label} className="flex items-center gap-1">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors
            ${i < current  ? "bg-blue-600 text-white"
            : i === current ? "bg-blue-100 text-blue-700 ring-2 ring-blue-400"
            : "bg-gray-100 text-gray-400"}`}>
            {i < current ? "✓" : i + 1}
          </div>
          <span className={`text-xs hidden sm:inline ${i === current ? "text-blue-700 font-medium" : "text-gray-400"}`}>
            {label}
          </span>
          {i < steps.length - 1 && (
            <div className={`h-px w-5 mx-1 ${i < current ? "bg-blue-400" : "bg-gray-200"}`} />
          )}
        </div>
      ))}
    </div>
  );
}
