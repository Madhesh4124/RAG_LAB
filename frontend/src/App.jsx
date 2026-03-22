import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Setup   from "./pages/Setup";
import Preview from "./pages/Preview";
import Compare from "./pages/Compare";

function Nav() {
  const link = ({ isActive }) =>
    `text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${isActive ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:text-gray-800 hover:bg-gray-100"}`;
  return (
    <nav className="border-b border-gray-200 bg-white px-6 py-3 flex items-center gap-1">
      <span className="font-bold text-gray-900 mr-4">🔬 RAG Lab</span>
      <NavLink to="/setup"   className={link}>Setup</NavLink>
      <NavLink to="/preview" className={link}>Chunk Preview</NavLink>
      <NavLink to="/compare" className={link}>Compare</NavLink>
    </nav>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Nav />
       <Routes>
  <Route path="/"        element={<Setup />} />
  <Route path="/setup"   element={<Setup />} />
  <Route path="/preview" element={<Preview />} />
  <Route path="/compare" element={<Compare />} />
  <Route path="/chat"    element={
    <div className="flex items-center justify-center h-96 text-gray-400">
      <p>Chat coming in Phase 6 🚧</p>
    </div>
  } />
  </Routes>
      </div>
    </BrowserRouter>
  );
}
