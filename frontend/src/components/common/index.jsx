import React from "react";
import { IconCheck } from "./Icons";

// ── Button (Linear / Raycast developer style) ────────────────────────────────
export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  className = "",
  type = "button",
  trailingIcon,
  leadingIcon,
  size = "md",
}) {
  const sizes = {
    sm: "h-7 px-2.5 text-[11px] gap-1.5",
    md: "h-8.5 px-3.5 text-xs gap-2",
    lg: "h-10 px-4 text-sm gap-2.5",
  };

  const base =
    "relative inline-flex items-center justify-center font-medium rounded-lg " +
    "transition-all duration-150 ease-out " +
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50 focus-visible:ring-offset-1 focus-visible:ring-offset-zinc-950 " +
    "disabled:opacity-40 disabled:pointer-events-none cursor-pointer select-none whitespace-nowrap";

  const variants = {
    primary:
      "bg-amber-500 text-zinc-950 font-semibold hover:bg-amber-400 active:bg-amber-600 shadow-sm",
    secondary:
      "bg-zinc-900 text-zinc-200 border border-zinc-800 hover:bg-zinc-850 hover:border-zinc-700 active:bg-zinc-800",
    ghost:
      "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-850 active:bg-zinc-800",
    danger:
      "bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 active:bg-red-500/30",
    success:
      "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${sizes[size] || sizes.md} ${variants[variant] || variants.primary} ${className}`}
    >
      {leadingIcon && <span className="flex-shrink-0 opacity-80">{leadingIcon}</span>}
      <span>{children}</span>
      {trailingIcon && <span className="flex-shrink-0 opacity-80">{trailingIcon}</span>}
    </button>
  );
}

// ── Card (Single clean structured surface, NO double-bezel) ─────────────────
export function Card({ children, className = "", onClick, selected }) {
  return (
    <div
      onClick={onClick}
      className={`rounded-xl border p-5 transition-all duration-150 ${
        selected
          ? "border-amber-500/60 bg-zinc-900/90 shadow-sm"
          : "border-zinc-800/80 bg-zinc-900/50 hover:border-zinc-700/80"
      } ${onClick ? "cursor-pointer" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

// ── ProgressBar ──────────────────────────────────────────────────────────────
export function ProgressBar({ value, max = 100, color = "amber" }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const colors = {
    amber: "bg-amber-500",
    emerald: "bg-emerald-500",
    blue: "bg-blue-500",
  };

  return (
    <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div
        className={`h-full transition-all duration-300 ease-out rounded-full ${colors[color] || colors.amber}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ── Spinner ──────────────────────────────────────────────────────────────────
export function Spinner({ label, size = "md" }) {
  const sizes = {
    sm: "h-3.5 w-3.5 border-[1.5px]",
    md: "h-5 w-5 border-2",
    lg: "h-8 w-8 border-2",
  };
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-6" role="status" aria-label={label || "Loading"}>
      <div
        className={`animate-spin rounded-full border-zinc-700 border-t-amber-500 ${sizes[size] || sizes.md}`}
      />
      {label && <p className="text-xs text-zinc-400 font-medium">{label}</p>}
    </div>
  );
}

// ── Badge ────────────────────────────────────────────────────────────────────
export function Badge({ children, color = "ghost", className = "" }) {
  const colors = {
    amber:   "border-amber-500/30 bg-amber-500/10 text-amber-400",
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    blue:    "border-blue-500/30 bg-blue-500/10 text-blue-400",
    red:     "border-red-500/30 bg-red-500/10 text-red-400",
    ghost:   "border-zinc-800 bg-zinc-900 text-zinc-400",
  };
  return (
    <span
      className={`inline-flex items-center font-mono text-[11px] px-2 py-0.5 rounded-md border ${colors[color] || colors.ghost} ${className}`}
    >
      {children}
    </span>
  );
}

// ── EyebrowTag (Clean section header / breadcrumb) ───────────────────────────
export function EyebrowTag({ children }) {
  return (
    <div className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
      <span className="w-1.5 h-1.5 rounded-sm bg-amber-500/80 inline-block" />
      {children}
    </div>
  );
}

// ── StepIndicator ─────────────────────────────────────────────────────────────
export function StepIndicator({ steps, current }) {
  return (
    <div className="flex items-center gap-2" role="list" aria-label="Progress steps">
      {steps.map((label, i) => (
        <div key={label} className="flex items-center gap-2" role="listitem">
          <div
            className={`w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-mono font-medium transition-colors ${
              i < current
                ? "bg-amber-500 text-zinc-950"
                : i === current
                  ? "bg-zinc-100 text-zinc-950 font-bold"
                  : "bg-zinc-800/80 text-zinc-500 border border-zinc-700/50"
            }`}
          >
            {i < current ? <IconCheck size={10} /> : i + 1}
          </div>
          <span
            className={`text-xs font-medium tracking-tight ${
              i === current ? "text-zinc-100 font-semibold" : i < current ? "text-zinc-400" : "text-zinc-600"
            }`}
          >
            {label}
          </span>
          {i < steps.length - 1 && (
            <div
              className={`h-px w-6 transition-colors ${
                i < current ? "bg-amber-500/40" : "bg-zinc-800"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ── InlineAlert ───────────────────────────────────────────────────────────────
export function InlineAlert({ type = "error", children, className = "" }) {
  const styles = {
    error:   "border-red-500/25 bg-red-500/[0.08] text-red-300",
    warning: "border-amber-500/25 bg-amber-500/[0.08] text-amber-300",
    success: "border-emerald-500/25 bg-emerald-500/[0.08] text-emerald-300",
    info:    "border-blue-500/25 bg-blue-500/[0.08] text-blue-300",
  };
  return (
    <div
      role="alert"
      className={`rounded-lg border px-3.5 py-2.5 text-xs leading-relaxed ${styles[type] || styles.error} ${className}`}
    >
      {children}
    </div>
  );
}

// ── Divider ───────────────────────────────────────────────────────────────────
export function Divider({ label, className = "" }) {
  if (!label) {
    return <div className={`h-px bg-zinc-800 ${className}`} />;
  }
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="flex-1 h-px bg-zinc-800" />
      <span className="font-mono text-[10px] text-zinc-500 uppercase tracking-wider">
        {label}
      </span>
      <div className="flex-1 h-px bg-zinc-800" />
    </div>
  );
}
