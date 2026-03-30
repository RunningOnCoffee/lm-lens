import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Profiles from './pages/Profiles';
import ProfileEditor from './pages/ProfileEditor';
import ProfileView from './pages/ProfileView';
import Scenarios from './pages/Scenarios';
import ScenarioEditor from './pages/ScenarioEditor';

function Sidebar() {
  const linkClass = ({ isActive }) =>
    `block px-4 py-2.5 rounded-lg text-sm transition-colors ${
      isActive
        ? 'bg-surface-700 text-accent'
        : 'text-gray-400 hover:text-gray-200 hover:bg-surface-800'
    }`;

  return (
    <aside className="w-56 bg-surface-800 border-r border-surface-600 flex flex-col h-screen sticky top-0">
      <div className="px-4 py-5 border-b border-surface-600">
        <h1 className="font-heading font-bold text-lg text-accent tracking-wide">
          LM Lens
        </h1>
        <p className="text-xs text-gray-500 mt-0.5">LLM Benchmark Tool</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        <NavLink to="/" className={linkClass} end>Dashboard</NavLink>
        <NavLink to="/benchmarks" className={linkClass}>Benchmarks</NavLink>
        <NavLink to="/scenarios" className={linkClass}>Scenarios</NavLink>
        <NavLink to="/profiles" className={linkClass}>Profiles</NavLink>
      </nav>
      <div className="p-3 border-t border-surface-600">
        <div className="text-xs text-gray-600 px-4 py-2">v0.1.0</div>
      </div>
    </aside>
  );
}

function Placeholder({ title }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h2 className="font-heading text-2xl text-gray-400 mb-2">{title}</h2>
        <p className="text-gray-600 text-sm">Coming soon</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/benchmarks" element={<Placeholder title="Benchmarks" />} />
            <Route path="/scenarios" element={<Scenarios />} />
            <Route path="/scenarios/new" element={<ScenarioEditor />} />
            <Route path="/scenarios/:id/edit" element={<ScenarioEditor />} />
            <Route path="/profiles" element={<Profiles />} />
            <Route path="/profiles/new" element={<ProfileEditor />} />
            <Route path="/profiles/:id/edit" element={<ProfileEditor />} />
            <Route path="/profiles/:id" element={<ProfileView />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
