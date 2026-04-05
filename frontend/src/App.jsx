import React from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import Setup   from "./pages/Setup";
import Preview from "./pages/Preview";
import Compare from "./pages/Compare";
import Chat from "./pages/Chat";
import QuickChat from "./pages/QuickChat";
import Admin from "./pages/Admin";
import Login from "./pages/Login";
import PasswordReset from "./pages/PasswordReset";
import ModeSelect from "./pages/ModeSelect";
import { useAuth } from "./hooks/useAuth";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="min-h-screen grid place-items-center text-gray-500">Loading...</div>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return children;
}

function AdminRoute({ children }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();

  if (loading) {
    return <div className="min-h-screen grid place-items-center text-gray-500">Loading...</div>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (!isAdmin) {
    return <Navigate to="/mode-select" replace />;
  }
  return children;
}

function Nav() {
  const { isAuthenticated, isAdmin, user, logout } = useAuth();
  const navigate = useNavigate();

  if (!isAuthenticated) return null;

  const link = ({ isActive }) =>
    `text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${isActive ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:text-gray-800 hover:bg-gray-100"}`;

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <nav className="border-b border-gray-200 bg-white px-6 py-3 flex items-center gap-1 justify-between">
      <div className="flex items-center gap-1">
      <span className="font-bold text-gray-900 mr-4">RAG Lab</span>
      <NavLink to="/mode-select" className={link}>Modes</NavLink>
      <NavLink to="/compare" className={link}>Compare</NavLink>
      <NavLink to="/chat"    className={link}>Chat</NavLink>
      <NavLink to="/setup" className={link}>Custom Chat</NavLink>
      {isAdmin && <NavLink to="/admin" className={link}>Admin</NavLink>}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500">{user?.username || user?.email}</span>
        <button onClick={onLogout} className="text-sm text-red-600 hover:text-red-700">Logout</button>
      </div>
    </nav>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Nav />
       <Routes>
  <Route path="/" element={<Navigate to="/login" replace />} />
  <Route path="/login" element={<Login />} />
  <Route path="/password-reset" element={<PasswordReset />} />
  <Route path="/mode-select" element={<ProtectedRoute><ModeSelect /></ProtectedRoute>} />
  <Route path="/setup" element={<ProtectedRoute><Setup /></ProtectedRoute>} />
  <Route path="/preview" element={<ProtectedRoute><Preview /></ProtectedRoute>} />
  <Route path="/compare" element={<ProtectedRoute><Compare /></ProtectedRoute>} />
  <Route path="/chat" element={<ProtectedRoute><QuickChat /></ProtectedRoute>} />
  <Route path="/custom-chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
  <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
  <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes>
      </div>
    </BrowserRouter>
  );
}
