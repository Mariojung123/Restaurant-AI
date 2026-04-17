import { Navigate, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import Chat from './pages/Chat.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Invoice from './pages/Invoice.jsx';
import Recipe from './pages/Recipe.jsx';
import Settings from './pages/Settings.jsx';

// Top-level shell: global navbar + routed page content.
function App() {
  return (
    <div className="flex min-h-full flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/recipe" element={<Recipe />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/invoice" element={<Invoice />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
