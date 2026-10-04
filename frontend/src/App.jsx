import React from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import Setup from "./pages/Setup";
import Preview from "./pages/Preview";
import Compare from "./pages/Compare";
import Chat from "./pages/Chat";
import QuickChat from "./pages/QuickChat";
import Admin from "./pages/Admin";
import Login from "./pages/Login";
import PasswordReset from "./pages/PasswordReset";
import ModeSelect from "./pages/ModeSelect";
import { useAuth } from "./hooks/useAuth";
import { SessionProvider } from "./hooks/useSession";
import ErrorBoundary from "./components/common/ErrorBoundary";
import {
  IconHome,
  IconAdminShield,
  IconLogOut,
  IconUser,
} from "./components/common/Icons";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center bg-zinc-950">
        <div className="flex flex-col items-center gap-2.5">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-800 border-t-amber-500" />
          <p className="font-mono text-xs text-zinc-500">Authenticating session…</p>
        </div>
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return children;
}

function AdminRoute({ children }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center bg-zinc-950">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-800 border-t-amber-500" />
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/mode-select" replace />;
  return children;
}

// ── Clean Top Navigation Bar ─────────────────────────────────────────────────
// Only retains "Modes" (and "Admin" if admin). No PDF filename or extra switches.
function TopNav() {
  const { isAuthenticated, isAdmin, user, logout } = useAuth();
  const navigate = useNavigate();

  if (!isAuthenticated) return null;

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-40 w-full h-14 border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur-md">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Brand + Modes tab */}
        <div className="flex items-center gap-5">
          <NavLink to="/mode-select" className="flex items-center gap-2 group cursor-pointer select-none">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-900 border border-zinc-800 group-hover:border-zinc-700 transition-colors">
              <span className="font-mono text-xs font-bold text-amber-500">R</span>
            </div>
            <span className="text-sm font-semibold tracking-tight text-zinc-100">
              RAG<span className="text-amber-500">Lab</span>
            </span>
          </NavLink>

          <div className="h-4 w-px bg-zinc-800" />

          {/* Navigation Links: ONLY "Modes" and "Admin" */}
          <nav className="flex items-center gap-1">
            <NavLink
              to="/mode-select"
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  isActive
                    ? "bg-zinc-800 text-zinc-100 font-semibold"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
                }`
              }
            >
              <IconHome size={14} className="opacity-80" />
              <span>Modes</span>
            </NavLink>

            {isAdmin && (
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    isActive
                      ? "bg-zinc-800 text-zinc-100 font-semibold"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
                  }`
                }
              >
                <IconAdminShield size={14} className="opacity-80" />
                <span>Admin</span>
              </NavLink>
            )}
          </nav>
        </div>

        {/* Right side: User Profile & Sign Out */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-zinc-900/60 border border-zinc-800/80 text-xs text-zinc-400">
            <IconUser size={12} className="text-zinc-500 flex-shrink-0" />
            <span className="font-medium text-zinc-300 max-w-[140px] truncate">
              {user?.username || user?.email}
            </span>
            {isAdmin && (
              <span className="font-mono text-[9px] uppercase px-1 py-0.2 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded font-semibold">
                Admin
              </span>
            )}
          </div>

          <button
            onClick={onLogout}
            title="Sign out"
            aria-label="Sign out"
            className="flex h-8 w-8 items-center justify-center rounded-md border border-zinc-800 bg-zinc-900 text-zinc-400 hover:bg-red-500/10 hover:border-red-500/25 hover:text-red-400 transition-colors cursor-pointer"
          >
            <IconLogOut size={13} />
          </button>
        </div>
      </div>
    </header>
  );
}

// ── Root App ─────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
          <TopNav />
          <main className="flex-1">
            <ErrorBoundary>
              <Routes>
                <Route path="/"               element={<Navigate to="/login" replace />} />
                <Route path="/login"          element={<Login />} />
                <Route path="/password-reset" element={<PasswordReset />} />
                <Route path="/mode-select"    element={<ProtectedRoute><ModeSelect /></ProtectedRoute>} />
                <Route path="/setup"          element={<ProtectedRoute><Setup /></ProtectedRoute>} />
                <Route path="/preview"        element={<ProtectedRoute><Preview /></ProtectedRoute>} />
                <Route path="/compare"        element={<ProtectedRoute><Compare /></ProtectedRoute>} />
                <Route path="/chat"           element={<ProtectedRoute><QuickChat /></ProtectedRoute>} />
                <Route path="/custom-chat"    element={<ProtectedRoute><Chat /></ProtectedRoute>} />
                <Route path="/admin"          element={<AdminRoute><Admin /></AdminRoute>} />
                <Route path="*"               element={<Navigate to="/login" replace />} />
              </Routes>
            </ErrorBoundary>
          </main>
        </div>
      </SessionProvider>
    </BrowserRouter>
  );
}
